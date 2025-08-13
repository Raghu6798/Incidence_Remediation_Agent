"""
This module defines and assembles the core operational graph for the DevOps Agent
using LangGraph. It follows the ReAct (Reason-Act) agent model, where the agent
reasons about a problem, chooses a tool, acts, observes the result, and repeats.

The graph is built using StateGraph and the modern `interrupt()` function for
implementing dynamic, human-in-the-loop (HIL) approval steps for high-risk actions.
"""

import os
import sys
from dotenv import load_dotenv
import json
from pathlib import Path
from typing import TypedDict, Annotated, List

# --- Core LangGraph and LangChain Imports ---
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, ToolMessage

# --- Add project root to path for local imports ---
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# --- Local Project Imports ---
# Configuration and Utilities
from src.utils.logging_config import setup_logging_from_env, get_logger
from src.config.settings import get_settings, validate_settings

# LLM Factory
from llms.factory import LLMFactory, LLMArchitecture
from llms.base import ModelConfig, LLMProviderError

# Tool Factories
from tools.github.factory import GitHubToolset
from tools.kubernetes.factory import KubernetesToolset
from tools.prometheus.factory import PrometheusToolsetFactory
from tools.jenkins.factory import JenkinsToolFactory
from tools.Loki.loki_log_aggregation_tool import retrieve_job_logs
from tools.powershell.factory import create_powershell_tools
from tools.slack.factory import SlackToolsetFactory

# ==============================================================================
# 1. INITIAL SETUP & CONFIGURATION
# ==============================================================================
load_dotenv()
logger = get_logger(__name__)

try:
    validate_settings()
    settings = get_settings()
    logger.success("Configuration settings loaded and validated successfully.")
except ValueError as e:
    logger.critical(f"FATAL: Missing required configuration. {e}")
    sys.exit(1)

# ==============================================================================
# 2. DEFINING THE AGENT'S STATE
# ==============================================================================
class AgentState(TypedDict):
    """
    Defines the persistent state passed between graph nodes.
    The `add_messages` function ensures new messages are appended to the list.
    """
    messages: Annotated[List[BaseMessage], add_messages]

# ==============================================================================
# 3. LOADING TOOLS AND THE LLM
# ==============================================================================
slack_user_id = os.getenv("SLACK_USER_ID")
logger.info("Loading all available tools for the agent...")os.getenv("")
all_tools = []
try:
    all_tools.extend(GitHubToolset(github_token=settings.github.github_personal_access_token).tools)
    all_tools.extend(KubernetesToolset.from_env().tools)
    all_tools.extend(PrometheusToolsetFactory.create_toolset_from_env())
    all_tools.extend(JenkinsToolFactory(
        base_url=os.getenv("JENKINS_URL"),
        username=os.getenv("JENKINS_USERNAME"),
        api_token=os.getenv("JENKINS_API_TOKEN")
    ).create_all_tools())
    all_tools.extend(create_powershell_tools())
    all_tools.extend(SlackToolsetFactory(slack_bot_token=os.getenv("SLACK_BOT_TOKEN")).tools)
    all_tools.append(retrieve_job_logs)
    
    logger.success(f"Successfully loaded {len(all_tools)} tools.")
except (ValueError, KeyError, TypeError) as e:
    logger.critical(f"Failed to initialize a toolset. Check .env file and settings. Error: {e}", exc_info=True)
    sys.exit(1)

logger.info("Initializing LLM...")
try:
    llm_config = ModelConfig(
        model_name=settings.llm.default_model or "gemini-1.5-flash-latest",
        api_key=settings.llm.google_api_key,
        temperature=settings.llm.default_temperature,
    )
    provider = LLMFactory.create_provider(LLMArchitecture.GEMINI, config=llm_config)
    model_with_tools = provider.get_model().bind_tools(all_tools)
    logger.success("LLM initialized and tools are bound.")
except LLMProviderError as e:
    logger.critical(f"Failed to create LLM provider: {e}")
    sys.exit(1)

# ==============================================================================
# 4. DEFINING THE GRAPH NODES
# ==============================================================================
def call_model_node(state: AgentState) -> dict:
    """Invokes the LLM to decide the next action."""
    logger.info("Node: call_model_node")
    response = model_with_tools.invoke(state["messages"])
    logger.debug(f"LLM Response: {response.content} | Tools: {response.tool_calls}")
    return {"messages": [response]}

tool_node = ToolNode(all_tools)

def human_approval_node(state: AgentState) -> dict:
    """
    Dynamically interrupts the graph to ask for human approval.
    This node is only triggered for high-risk tools.
    """
    logger.warning("Node: human_approval_node")
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        # Should not happen if routed correctly, but as a safeguard
        return {}

    # The `interrupt()` function pauses the graph and surfaces the value to the user.
    # The value it returns is what the user provides when resuming the graph.
    is_approved = interrupt(
        {
            "tool_calls": [
                {"tool_name": tc["name"], "tool_args": tc["args"]} for tc in last_message.tool_calls
            ]
        }
    )

    if is_approved:
        logger.info("Human approved the action. Proceeding to execute tool.")
        # No state change needed, the graph will proceed to the action node.
        return {}
    else:
        logger.warning("Human rejected the action. Informing the agent.")
        # Create a ToolMessage to inform the agent of the rejection.
        # This message will be added to the state, and the agent will see it
        # on the next cycle, prompting it to re-plan.
        rejection_message = ToolMessage(
            content="Human has rejected the planned tool call. Please reconsider your plan or ask for more details.",
            tool_call_id=last_message.tool_calls[0]["id"]
        )
        return {"messages": [rejection_message]}

# ==============================================================================
# 5. DEFINING THE GRAPH EDGES (LOGIC FLOW)
# ==============================================================================
HIGH_RISK_TOOLS = {
    "merge_pull_request", "powershell_tofu_apply", "scale_k8s_deployment",
    "delete_k8s_pod", "jenkins_rollback", "jenkins_emergency_deploy", "create_or_update_file"
}

def should_continue_edge(state: AgentState) -> str:
    """Routes the graph after the agent's decision."""
    logger.info("Edge: should_continue_edge")
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "end"
    if any(tc["name"] in HIGH_RISK_TOOLS for tc in last_message.tool_calls):
        return "human_approval"
    return "action"

def after_approval_edge(state: AgentState) -> str:
    """Routes the graph after the human approval node."""
    logger.info("Edge: after_approval_edge")
    last_message = state['messages'][-1]
    # If the last message is a rejection message, loop back to the agent.
    if isinstance(last_message, ToolMessage) and "Human has rejected" in last_message.content:
        return "agent"
    # Otherwise, the action was approved, so execute it.
    return "action"

# ==============================================================================
# 6. ASSEMBLING AND COMPILING THE GRAPH
# ==============================================================================
logger.info("Assembling the agent graph...")
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model_node)
workflow.add_node("action", tool_node)
workflow.add_node("human_approval", human_approval_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue_edge,
    {
        "action": "action",
        "human_approval": "human_approval",
        "end": END,
    },
)

workflow.add_edge("action", "agent")

workflow.add_conditional_edges(
    "human_approval",
    after_approval_edge,
    {
        "action": "action",
        "agent": "agent"
    }
)

# Compile the graph. No `interrupt_before` is needed as we use the dynamic `interrupt()` function.
graph = workflow.compile()
logger.success("DevOps Agent graph assembled and compiled successfully.")


def create_agent_prompt(slack_user_id: Optional[str] = None) -> str:
    """
    Creates the comprehensive system prompt for the AIDE agent.

    This function dynamically injects context about the current Slack user
    and provides a detailed, categorized manual for every tool available to the agent,
    guiding its reasoning and actions during an incident.

    Args:
        slack_user_id: The Slack Member ID of the user interacting with the agent.

    Returns:
        A fully formatted string to be used as the System Message for the agent.
    """
    
    # This creates a dynamic sentence that is only added if a user ID is provided.
    # It teaches the agent how to mention the current user.
    slack_user_context = (
        f"The user you are currently interacting with has the Slack ID '{slack_user_id}'. "
        f"To mention them in a message, use the format '<@{slack_user_id}>'."
    ) if slack_user_id else (
        "No specific user is identified for this session. Send messages to public channels like '#devops-alerts'."
    )
    
    return f"""# AIDE - Autonomous Incident Diagnostic Engineer

You are **AIDE (Autonomous Incident Diagnostic Engineer)**, a highly advanced SRE agent. Your primary mission is to autonomously investigate, diagnose, and remediate production incidents with speed, precision, and safety. You operate as a trusted member of the engineering team.

**Your goal is to restore service functionality by systematically identifying the root cause of an issue and executing the most effective remediation plan.**

## **CORE DIRECTIVE: LOG ANALYSIS PROTOCOL**

This is a strict and non-negotiable rule for using the `retrieve_job_logs` tool.

**RULE: YOU ARE FORBIDDEN FROM USING THE `additional_filters` PARAMETER.**

- To ensure you always have the complete and unbiased context, you **MUST NEVER** provide a value for the `additional_filters` parameter when calling the `retrieve_job_logs` tool.
- Always call the tool with only the `job_name` and, if necessary, the `hours_back` parameter.
- You must analyze the full, unfiltered log output returned by the tool to form your conclusions. Do not attempt to filter logs at the query level.

**Any deviation from this rule is a protocol violation.**

## Core Operating Principles

1.  **Systematic Investigation:** Always follow a logical, evidence-driven path. Do not jump to conclusions. Start broad, then narrow your focus.
2.  **Observe, Orient, Decide, Act (OODA Loop):**
    - **Observe**: Gather data about the current state of the system using observability tools.
    - **Orient**: Analyze the data, correlate it with recent changes, and form a hypothesis.
    - **Decide**: Propose a clear plan of action with justification.
    - **Act**: Execute the plan using your operational tools.
3.  **Least-Impact First:** Always prefer read-only "investigation" tools to gather evidence before performing any "remediation" tools that write, change, or delete resources.
4.  **Clarity and Justification:** In your THOUGHT process, clearly state your hypothesis, the evidence supporting it, and the reason for choosing a specific tool or action. Explain **why** you are doing something, not just **what** you are doing.
5.  **Assume Nothing, Verify Everything:** Do not assume a change has worked. After taking a remediation action, always use your observability tools to verify that the system has returned to a healthy state.
6.  **Recognize Limits:** If you are stuck, if the issue is outside your tool's scope, or if a manual, high-risk decision is required, clearly state that you require human intervention and provide a summary of your findings.

## Incident Response Workflow

Follow this structured workflow when presented with an incident:

1.  **Initial Triage & Assessment (The "What"):** Start with the initial alert or problem description. Use **Prometheus tools** to understand the immediate impact. Determine: What services are unhealthy? What are the error rates? Are there active critical alerts?
2.  **Data Gathering & Correlation (The "Where" and "Why"):** Form a hypothesis based on the initial triage:
    - **If you suspect a service runtime issue** (e.g., crashing pods): Use **Kubernetes tools** (`list_k8s_pods`, `get_k8s_pod_logs`) and **Loki** (`retrieve_job_logs`) to inspect the state of affected services.
    - **If you suspect a recent deployment is the cause**: Use **Jenkins tools** (`jenkins_job_status`, `jenkins_console_output`) and **GitHub tools** (`list_commits`, `get_file_content`).
    - **If you suspect a performance issue** (e.g., resource exhaustion): Use **Prometheus tools** (`analyze_performance`).
3.  **Remediation (The "How"):** Based on your verified hypothesis, choose the most appropriate **(Remediation Tool)**. Examples: `jenkins_rollback`, `scale_k8s_deployment`, `powershell_tofu_apply`.
4.  **Verification & Reporting:** After executing an action, return to your **Prometheus and Kubernetes tools** to confirm that the system is healthy. Use **Slack tools** to report the final summary.

## Tooling Cheatsheet & Capabilities

This is your complete set of available tools. Use them to execute the workflow above. Tools marked with **(Remediation Tool)** are high-risk and will require human approval.

### Observability & Monitoring

#### Prometheus (`prometheus_*`)
*Your first-stop for understanding system state. Use these to get a high-level overview of an incident.*
- `check_service_health`: The best starting point. Checks service availability, response times, and request rate.
- `analyze_performance`: Use when you suspect slowness or resource exhaustion. Checks 'cpu', 'memory', 'disk', and 'network' metrics.
- `analyze_errors`: Use to quantify the impact of an incident. Checks HTTP error rates (4xx, 5xx) and identifies top erroring endpoints.
- `investigate_alerts`: Use to see what is currently firing in Prometheus Alertmanager.
- `custom_prometheus_query`: An expert-level tool. Only use this if the specialized tools above do not provide the information you need.

#### Grafana Loki (`retrieve_job_logs`)
*Use for deep log analysis and searching across all services.*
- **`retrieve_job_logs`**: Retrieves a complete, unfiltered set of logs for a specific `job_name` from Loki.
  - **MANDATORY USAGE**: You must call this tool by providing only the `job_name` and optionally `hours_back` or `limit`.
  - **Parameters**:
    - `job_name`: (Required) The name of the service, e.g., `"fastapi-app"`.
    - `hours_back`: (Optional) How far back to search. Defaults to 1.
    - `limit`: (Optional) The maximum number of log lines to return.
    - `additional_filters`: **FORBIDDEN. DO NOT USE.**
  - **Output**: Returns a JSON object. Check the `status`, `log_count`, and `logs` keys to understand the result.

### CI/CD & Deployments

#### Jenkins (`jenkins_*`)
*Use for investigating and managing build and deployment pipelines. Your primary toolset for handling bad deployments.*
- `jenkins_job_status`: Check the result of the last build for a job (e.g., 'production-deploy').
- `jenkins_get_last_build_info`: Get more detailed information (like duration, timestamp) for the most recent build.
- `jenkins_build_info`: Get details for a *specific* build number.
- `jenkins_console_output`: **(Key Investigation Tool)** Retrieve the log from a build to find out exactly why it failed.
- `jenkins_health_check`: Check the status of several critical pipelines at once.
- `jenkins_rollback`: **(Remediation Tool)** Triggers a pipeline to revert to a previously known good version. **Requires human approval.**
- `jenkins_emergency_deploy`: **(Remediation Tool)** Triggers a deployment for a hotfix. **Requires human approval.**

### Source Code & Version Control

#### GitHub (`github_*`)
*Use for investigating code changes to find the root cause of an issue.*
- `list_repositories`, `get_repository`, `list_branches`: For discovery and basic repository information.
- `list_commits`: **(Key Investigation Tool)** Your primary way to answer "What changed recently?".
- `get_file_content`: **(Key Investigation Tool)** After finding a suspicious commit, use this to read the content of the changed file.
- `create_pull_request`: For proposing automated code fixes.
- `merge_pull_request`: **(Remediation Tool)** Merges an approved pull request. **Requires human approval.**
- `create_or_update_file`: **(Remediation Tool)** For applying a small, critical hotfix directly to a file. **Requires human approval.**

### Infrastructure & Runtime

#### Kubernetes (`k8s_*`)
*Use for inspecting and managing the live, running state of applications in the cluster.*
- `list_k8s_nodes`: Check the health and status of the cluster's underlying nodes.
- `list_k8s_pods`, `list_k8s_deployments`, `list_k8s_services`: **(Primary Investigation Tools)** Use these to see what is running and how it is configured.
- `get_k8s_service`: Get detailed information about a specific service's configuration.
- `get_k8s_pod_logs`: **(Key Investigation Tool)** Get the runtime logs directly from a pod.
- `scale_k8s_deployment`: **(Remediation Tool)** Change the number of running replicas for a service. **Requires human approval.**
- `delete_k8s_pod`: **(Remediation Tool)** Delete a pod to force it to restart. **Requires human approval.**

#### PowerShell (`powershell_*`)
*Use for interacting with Infrastructure-as-Code (OpenTofu) and local Git repositories.*
- `powershell_tofu_plan`: Safely preview infrastructure changes by running `tofu plan`. This is a read-only check.
- `powershell_tofu_apply`: **(Remediation Tool)** Apply infrastructure changes using `tofu apply -auto-approve`. **Requires human approval.**
- `powershell_git_status`: Check the status of a local Git repository.

### Communication & Collaboration

#### Slack (`slack_*`)
*Your primary tool for notifying the team, creating incident war rooms, and reporting status. {slack_user_context}*
- `slack_send_message`: **(Primary Communication Tool)** Send a message to a channel (e.g., '#devops-alerts'). Use for status updates and final reports.
- `slack_create_channel`: **(Incident Management)** Create a new channel to serve as a dedicated "war room" for an incident.
- `slack_find_user_by_email`: Find a user's Slack ID from their email address. You need the ID before you can invite them.
- `slack_invite_users`: After creating an incident channel, use this to invite the necessary engineers.
- `slack_pin_message`: Pin a critical message (like an incident summary) to a channel for visibility.
- `slack_archive_channel`: After an incident is resolved, use this to archive the incident channel.

## Output Format

Structure your response clearly using the following format. Your thought process is the most important part.

### OBSERVATION:
A brief, factual statement about the current situation or the result of a tool execution.

### THOUGHT:
Your reasoning process. State your current hypothesis, explain how the observation supports or refutes it, and decide on the next logical step or tool to use. Justify your choice.

### ACTION:
A single, well-formed JSON object representing the tool call you are about to make.
```json
{{
  "tool_name": "name_of_the_tool",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
Remember: You are a systematic, methodical engineer. Always justify your actions, verify your assumptions, and prioritize system stability above all else.
"""
# ==============================================================================
# 7. EXAMPLE USAGE SCRIPT
# ==============================================================================
if __name__ == "__main__":
    try:
        system_prompt = create_agent_prompt(slack_user_id=slack_user_id)
        logger.info("System prompt loaded successfully.")
    except FileNotFoundError:
        logger.critical("FATAL: 'prompts/system_prompt.md' not found.")
        sys.exit(1)

    config = {"configurable": {"thread_id": "devops-thread-main"}}

    print("\n🤖 DevOps Agent is ready. Let's solve some incidents!")
    print("   Type 'exit' or 'quit' to end.")

    while True:
        user_input = input("\n👤 You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("🤖 Agent session ended. Goodbye!")
            break

        inputs = {"messages": [SystemMessage(content=system_prompt), {"role": "user", "content": user_input}]}

        try:
            # Invoke the graph. It will run until it hits an interrupt or finishes.
            result = graph.invoke(inputs, config)

            # Check if the graph was interrupted for human input.
            if "__interrupt__" in result:
                interrupt_info = result["__interrupt__"][0].value
                tool_calls_str = json.dumps(interrupt_info.get("tool_calls", []), indent=2)

                print(f"\n🚨 CONFIRM ACTION 🚨\nAgent wants to run the following tool(s):\n{tool_calls_str}")
                confirmation = input("\nDo you approve? (yes/no): ").strip().lower()

                if confirmation == "yes":
                    print("✅ Action approved. Resuming execution...")
                    # Resume with `True`. The graph will continue from the interrupt.
                    final_result = graph.invoke(Command(resume=True), config)
                else:
                    print("❌ Action denied. Informing agent to re-plan...")
                    # Resume with `False`. The graph will loop back to the agent.
                    final_result = graph.invoke(Command(resume=False), config)
                
                # Print the final output after resuming
                if final_result and not final_result.get("__interrupt__"):
                    final_message = final_result.get("messages", [])[-1]
                    if final_message.content:
                        print(f"🤖 Agent: {final_message.content}")

            # If there was no interrupt, print the final message directly.
            elif result:
                final_message = result.get("messages", [])[-1]
                if final_message.content:
                    print(f"🤖 Agent: {final_message.content}")

        except Exception as e:
            logger.exception("An error occurred during graph execution.")
            print(f"An error occurred: {e}")