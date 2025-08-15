
import os
import sys
from dotenv import load_dotenv
import json
from pathlib import Path
from typing import TypedDict, Annotated, List, Optional

# --- Core LangGraph and LangChain Imports ---
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_core.messages import BaseMessage, SystemMessage

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
logger.info("Loading all available tools for the agent...")
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
    """Invokes the LLM to decide the next action or respond to the user."""
    logger.info("Node: call_model_node")
    response = model_with_tools.invoke(state["messages"])
    logger.debug(f"LLM Response: {response.content} | Tools: {response.tool_calls}")
    return {"messages": [response]}

# This node is responsible for executing the tools chosen by the agent
tool_node = ToolNode(all_tools)

# ==============================================================================
# 5. DEFINING THE GRAPH EDGES (LOGIC FLOW)
# ==============================================================================
def should_continue_edge(state: AgentState) -> str:
    """
    Routes the graph after the agent's decision.
    If the agent generated tool calls, route to the 'action' node.
    Otherwise, the conversation is over, so route to END.
    """
    logger.info("Edge: should_continue_edge")
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return "end"
    return "action"

# ==============================================================================
# 6. ASSEMBLING AND COMPILING THE GRAPH (Simplified)
# ==============================================================================
logger.info("Assembling the agent graph...")
workflow = StateGraph(AgentState)

# Define the nodes: the agent and the tool executor
workflow.add_node("agent", call_model_node)
workflow.add_node("action", tool_node)

# Set the entry point to the agent
workflow.set_entry_point("agent")

# Define the main conditional edge.
# After the agent speaks, decide whether to call a tool or end.
workflow.add_conditional_edges(
    "agent",
    should_continue_edge,
    {
        "action": "action", # If tool calls exist, go to the action node
        "end": END,         # Otherwise, finish.
    },
)

# After any action is taken, the results are processed by looping back to the agent.
workflow.add_edge("action", "agent")

# Compile the graph
# Add a checkpointer for conversation memory
graph = workflow.compile(checkpointer=MemorySaver())
logger.success("DevOps Agent graph assembled and compiled successfully.")


def create_agent_prompt(slack_user_id: Optional[str] = None) -> str:
    """
    Creates the comprehensive system prompt for the AIDE agent.
    """
    slack_user_context = (
        f"The user you are currently interacting with has the Slack ID '{slack_user_id}'. "
        f"To mention them in a message, use the format '<@{slack_user_id}>'."
    ) if slack_user_id else (
        "No specific user is identified for this session. Send messages to public channels like '#devops-alerts'."
    )
    
    return f"""# AIDE - Autonomous Incident Diagnostic Engineer

You are **AIDE (Autonomous Incident Diagnostic Engineer)**, a highly advanced SRE agent. Your primary mission is to autonomously investigate, diagnose, and remediate production incidents with speed, precision, and safety. You operate as a trusted member of the engineering team.

**Your goal is to restore service functionality by systematically identifying the root cause of an issue and executing the most effective remediation plan.**

## Core Operating Principles
1.  **Systematic Investigation:** Always follow a logical, evidence-driven path.
2.  **Observe, Orient, Decide, Act (OODA Loop):** Observe data, form a hypothesis, decide on a tool, and then act.
3.  **Least-Impact First:** Always prefer read-only "investigation" tools before using any tools that change state.
4.  **Clarity and Justification:** Clearly state your hypothesis and why you are choosing a specific tool.
5.  **Assume Nothing, Verify Everything:** After an action, use observability tools to verify the outcome.
6.  **Recognize Limits:** If you are stuck or need a high-risk decision, state that you require human intervention.

## Incident Response Workflow
1.  **Initial Triage & Assessment:** Use Prometheus tools to understand the immediate impact.
2.  **Data Gathering & Correlation:** Form a hypothesis and use Kubernetes, Loki, Jenkins, or GitHub tools to investigate.
3.  **Remediation:** Based on a verified hypothesis, choose the most appropriate remediation tool.
4.  **Verification & Reporting:** Confirm system health with Prometheus/Kubernetes and report via Slack.

## Tooling Cheatsheet & Capabilities

### Observability & Monitoring

#### Prometheus (`prometheus_*`)
*Your primary toolset for observing system and application health. It's crucial to use the right tool for the right job.*

**IMPORTANT: There are two types of services you can monitor:**
1.  **Application Services** (like `fastapi-app`): These are identified by a `service_name` (which corresponds to the `job` label in Prometheus). They provide metrics about application behavior (e.g., HTTP requests).
2.  **System Infrastructure** (like `node-exporter`): These are identified by an `instance` label (e.g., `node-exporter:9100`). They provide metrics about the machine's resources (e.g., CPU, memory).

**Tool Cheatsheet:**

- **`check_service_health`**: **(Use this first for application issues)**. Checks the overall health of a specific application using its `service_name`. It gives you availability (is it up?), latency (is it slow?), and request rate (is it busy?).
  - **Example**: `service_name="fastapi-app"`

- **`analyze_errors`**: Analyzes HTTP error rates for an application using its `service_name`. Use this to find out if an application is failing and which URL paths are causing the most errors.
  - **Example**: `service_name="fastapi-app"`

- **`analyze_performance`**: **(Use this for infrastructure issues)**. Analyzes low-level system resource usage (CPU, memory, disk, network) for a specific machine or container that is running a `node-exporter`. **This tool requires an `instance` label**, not a service name.
  - **Example**: If you suspect the machine running a service is overloaded, you would find its `instance` label first, then use this tool. `instance="node-exporter:9100"`, `metric_type="cpu"`.
  - **DO NOT** use this tool with an application's `service_name`. It will find no data.

- **`investigate_alerts`**: Checks for currently firing alerts in Alertmanager. Use this to see what Prometheus currently thinks is an active, critical problem across the entire system.

- **`custom_prometheus_query`**: **(Expert Use Only)**. Executes a raw PromQL query. Only use this if the specialized tools above cannot provide the information you need. You should be able to solve most problems without this.

#### Grafana Loki (`retrieve_job_logs`)
- Retrieves logs for a specific `job_name`. **MANDATORY: NEVER use the `additional_filters` parameter.**

### CI/CD & Deployments (Jenkins) & Source Code (GitHub)
- Use Jenkins tools (`jenkins_job_status`, `jenkins_console_output`, etc.) to investigate deployments.
- Use GitHub tools (`list_commits`, `get_file_content`, etc.) to investigate code changes.

### Infrastructure & Runtime (Kubernetes, PowerShell)
- Use Kubernetes tools (`list_k8s_pods`, `get_k8s_pod_logs`, etc.) to inspect the live state of applications.
- Use PowerShell tools (`powershell_tofu_plan`, `powershell_git_status`) for IaC and local git checks.

### Communication & Collaboration (Slack)
- Use Slack tools (`slack_send_message`, `slack_create_channel`, etc.) to notify the team. {slack_user_context}

## ACTION Format
Structure your tool calls as a JSON object.
```json
{{
  "tool_name": "name_of_the_tool",
  "parameters": {{
    "param1": "value1"
  }}
}}
Remember: You are a systematic, methodical engineer. Always justify your actions.
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