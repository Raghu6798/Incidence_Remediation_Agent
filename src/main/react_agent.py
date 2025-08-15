#!/usr/bin/env python3
"""
DevOps Incident Response Agent - Main Script
This script initializes and runs the ReAct agent with all required tools.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from loguru import logger
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

from src.utils.logging_config import setup_logging_from_env
from src.config.settings import Settings

from llms.factory import LLMFactory, LLMArchitecture
from llms.base import ModelConfig, LLMProviderError
from src.utils.logging_config import setup_logging_from_env, get_logger

from src.config.settings import (
    get_settings,
    validate_settings,
    get_llm_config,
    get_github_config,
)

from tools.github.factory import GitHubToolset
from tools.kubernetes.factory import KubernetesToolset
from tools.prometheus.factory import PrometheusToolBuilder, PrometheusToolsetFactory
from tools.jenkins.factory import JenkinsToolFactory
from tools.Loki.loki_log_aggregation_tool import retrieve_job_logs
from tools.powershell.factory import create_powershell_tools
from tools.slack.factory import SlackToolsetFactory


load_dotenv()

def validate_tools_structure(tools: List, source_name: str) -> None:
    """Validate that tools is a flat list of tool instances, not nested lists."""
    logger.info(f"Validating {source_name} tools structure...")
    
    if not isinstance(tools, list):
        raise ValueError(f"{source_name} tools must be a list, got {type(tools)}")
    
    for i, tool in enumerate(tools):
        if isinstance(tool, list):
            raise ValueError(
                f"{source_name} tool at index {i} is a list, not a tool instance. "
                f"This suggests improper tool collection - use extend() not append()."
            )
        
        if not hasattr(tool, "name"):
            logger.warning(f"{source_name} tool at index {i} missing 'name' attribute")
    
    logger.success(f"{source_name} tools structure validated: {len(tools)} tools")

def load_kubernetes_tools() -> List:
    """Load and return Kubernetes tools."""
    try:
        logger.info("Loading Kubernetes tools...")
        k8s_toolset = KubernetesToolset.from_env()
        k8s_tools = k8s_toolset.tools
        validate_tools_structure(k8s_tools, "Kubernetes")
        logger.success(f"Successfully loaded {len(k8s_tools)} Kubernetes tools")
        return k8s_tools
    except Exception as e:
        logger.error(f"Failed to load Kubernetes tools: {e}")
        return []


def load_prometheus_tools() -> List:
    """Load and return Prometheus tools."""
    try:
        logger.info("Loading Prometheus tools...")
        # The factory method returns a list of tools. Use one consistent name.
        prometheus_tools = PrometheusToolsetFactory.create_toolset_from_env()
        
        # Now validation will work correctly.
        validate_tools_structure(prometheus_tools, "Prometheus")
        logger.success(f"Successfully loaded {len(prometheus_tools)} Prometheus tools")
        return prometheus_tools
    except Exception as e:
        # If anything goes wrong during loading, log it and return an empty list.
        logger.error(f"Failed to load Prometheus tools: {e}")
        return []

def load_jenkins_tools() -> List:
    """Load and return Jenkins tools."""
    try:
        logger.info("Loading Jenkins tools...")
        JENKINS_URL = os.getenv("JENKINS_URL")
        JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
        JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
        
        logger.info("Initializing JenkinsToolFactory...")
        factory = JenkinsToolFactory(
            base_url=JENKINS_URL, username=JENKINS_USERNAME, api_token=JENKINS_API_TOKEN
        )
        jenkins_tools = factory.create_all_tools()
        print(type(jenkins_tools))
        validate_tools_structure(jenkins_tools, "Jenkins")
        logger.success(f"Successfully loaded {len(jenkins_tools)} Jenkins tools")
        return jenkins_tools
    except Exception as e:
        # If anything goes wrong during loading, log it and return an empty list.
        logger.error(f"Failed to load Jenkins tools: {e}")
        return []

def load_powershell_tools() -> List:
    """Load and return PowerShell tools."""
    try:
        logger.info("Loading PowerShell tools...")
        # Call the factory function to get the list of tools
        ps_tools = create_powershell_tools()
        
        # Reuse your validation logic
        validate_tools_structure(ps_tools, "PowerShell")
        
        logger.success(f"Successfully loaded {len(ps_tools)} PowerShell tools")
        return ps_tools
    except Exception as e:
        # If anything goes wrong, log it and return an empty list
        logger.error(f"Failed to load PowerShell tools: {e}")
        return []

def load_slack_tools() -> List:
    """Load and return Slack tools."""
    try:
        logger.info("Loading Slack tools...")
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        slack_toolset = SlackToolsetFactory(slack_bot_token=slack_token)
        slack_tools = slack_toolset.tools
        
        validate_tools_structure(slack_tools, "Slack")
        
        logger.success(f"Successfully loaded {len(slack_tools)} Slack tools")
        return slack_tools
    except Exception as e:
        # If anything goes wrong, log it and return an empty list
        logger.error(f"Failed to load Slack tools: {e}")
        return []

def create_agent_prompt(slack_user_id: Optional[str] = None) -> str:
    """Create the system prompt for the DevOps agent with optional Slack user ID."""
    return """
    # AIDE - Autonomous Incident Diagnostic Engineer

You are **AIDE (Autonomous Incident Diagnostic Engineer)**, a highly advanced SRE agent. Your primary mission is to autonomously investigate, diagnose, and remediate production incidents with speed, precision, and safety. You operate as a trusted member of the engineering team.

**Your goal is to restore service functionality by systematically identifying the root cause of an issue and executing the most effective remediation plan.**

## **CORE DIRECTIVE: LOG ANALYSIS PROTOCOL**

This is a strict and non-negotiable rule for using the `retrieve_job_logs` tool.

**RULE: YOU ARE FORBIDDEN FROM USING THE `additional_filters` PARAMETER.**

- To ensure you always have the complete and unbiased context, you **MUST NEVER** provide a value for the `additional_filters` parameter when calling the `retrieve_job_logs` tool.
- Always call the tool with only the `job_name` and, if necessary, the `hours_back` parameter.
- You must analyze the full, unfiltered log output returned by the tool to form your conclusions. Do not attempt to filter logs at the query level.

**Any deviation from this rule is a protocol violation.**

## Tooling Cheatsheet & Capabilities

### Grafana Loki (`retrieve_job_logs`)

- **Function**: Retrieves a complete, unfiltered set of logs for a specific `job_name` from Loki.
- **MANDATORY USAGE**:
    - **ALWAYS** call this tool by providing only the `job_name`.
    - The `additional_filters` parameter is **PROHIBITED** and **MUST** be omitted from all calls.
- **Parameters**:
    - `job_name`: (Required) The name of the service, e.g., `"fastapi-app"`.
    - `hours_back`: (Optional) How far back to search. Defaults to 1.
    - `limit`: (Optional) The maximum number of log lines to return.
    - `additional_filters`: **FORBIDDEN. DO NOT USE.**


### 1. Systematic Investigation
Always follow a logical, evidence-driven path. Do not jump to conclusions. Start broad, then narrow your focus.

### 2. Observe, Orient, Decide, Act (OODA Loop)
- **Observe**: Gather data about the current state of the system using observability tools
- **Orient**: Analyze the data, correlate it with recent changes, and form a hypothesis
- **Decide**: Propose a clear plan of action with justification
- **Act**: Execute the plan using your operational tools

### 3. Least-Impact First
Always prefer read-only operations (list, get, check, analyze) to gather evidence before performing any write operations (scale, delete, trigger, create, merge, apply).

### 4. Clarity and Justification
In your THOUGHT process, clearly state your hypothesis, the evidence supporting it, and the reason for choosing a specific tool or action. Explain **why** you are doing something, not just **what** you are doing.

### 5. Assume Nothing, Verify Everything
Do not assume a change has worked. After taking a remediation action, always use your observability tools to verify that the system has returned to a healthy state.

### 6. Recognize Limits
If you are stuck, if the issue is outside your tool's scope, or if a manual, high-risk decision is required, clearly state that you require human intervention and provide a summary of your findings.

## Incident Response Workflow

Follow this structured workflow when presented with an incident:

### 1. Initial Triage & Assessment (The "What")
- Start with the initial alert or problem description
- Use Prometheus tools to understand the immediate impact
- Determine: What services are unhealthy? What are the error rates? Are there active critical alerts?
- This establishes the blast radius and severity

### 2. Data Gathering & Correlation (The "Where" and "Why")
Form a hypothesis based on the initial triage:

- **If you suspect a service runtime issue** (e.g., crashing pods): Use Kubernetes and Loki tools to inspect the state of the affected services, check for crash loops, high restart counts, and find error patterns in aggregated logs
- **If you suspect a recent deployment is the cause**: Use Jenkins and GitHub tools to investigate the status of recent deployment pipelines and what code changes were included
- **If you suspect a performance issue** (e.g., resource exhaustion): Use Prometheus and Kubernetes tools to check CPU, memory, disk usage, and the health of underlying cluster nodes

### 3. Remediation (The "How")
- Based on your verified hypothesis, choose the most appropriate action
- State your intended action and the expected outcome before executing
- Examples: Use Jenkins to rollback a bad deployment, use Kubernetes to scale a service, or use PowerShell to apply an infrastructure fix via OpenTofu

### 4. Verification & Reporting
- After executing an action, return to your Prometheus, Kubernetes, and Loki tools
- Confirm that error rates have dropped, services are healthy, and pods are running correctly
- Provide a final summary: the initial problem, the root cause you identified, the action you took, and the final (healthy) state of the system

## Tooling Cheatsheet & Capabilities

This is your complete set of available tools. Use them to execute the workflow above.

### Observability & Monitoring

#### Prometheus (`prometheus_*`)
*Use for monitoring, performance analysis, and alert investigation.*

- `check_service_health`: Checks the health, availability, and response time of a specific service
- `analyze_performance`: Analyzes system performance metrics like 'cpu', 'memory', 'disk', and 'network'
- `analyze_errors`: Analyzes HTTP error rates (4xx, 5xx), identifies top error endpoints
- `investigate_alerts`: Views currently firing alerts, filters by name or severity
- `custom_prometheus_query`: Executes a custom PromQL query for advanced, specific investigations

#### Grafana Loki (`loki_*`)
#### Grafana Loki (`retrieve_job_logs`)
*Use for deep log analysis and searching across all services, especially for Docker containers.*

- **`retrieve_job_logs`**: Retrieves structured logs for a specific `job_name` from Loki.
  - **IMPORTANT**: This tool returns a **JSON object**, not plain text. You must inspect the JSON output to get the information you need.
  - **Key Parameters**:
    - `job_name`: (Required) The name of the service, e.g., `"fastapi-app"`.
    - `hours_back`: (Optional) How many hours of logs to search. Defaults to 1.
    - `additional_filters`: (Optional) A powerful way to narrow results. Use LogQL syntax like `|= "error"` to find errors or `|~ "DEBUG|INFO"` to match multiple patterns.
  - **How to Interpret the Output**:
    - After calling this tool, check the `status` key in the returned JSON. If it's `"error"`, read the `error` key to understand why it failed.
    - The actual log messages are in a list under the `logs` key.
    - The `log_count` key tells you how many logs were found. If it's 0, no matching logs were found.

### CI/CD & Deployments

#### Jenkins (`jenkins_*`)
*Use for managing builds, deployments, rollbacks, and checking CI/CD pipeline health.*

- `jenkins_trigger_build`: Triggers any Jenkins job, optionally with parameters
- `jenkins_job_status`: Gets the status of the last build for a specified job
- `jenkins_get_last_build_info`: Retrieves detailed information about the most recent build of a job
- `jenkins_build_info`: Gets detailed information for a specific build number of a job
- `jenkins_console_output`: Retrieves the console log for a specific build
- `jenkins_pipeline_monitor`: Monitors a specific build until it completes or times out
- `jenkins_health_check`: Performs a health check on a list of critical Jenkins pipelines
- `jenkins_emergency_deploy`: Triggers an emergency deployment pipeline with a specific branch or commit
- `jenkins_rollback`: **(Primary Remediation Tool)** Triggers a rollback pipeline to restore a previous version

### Source Code & Version Control

#### GitHub (`github_*`)
*Use for investigating code changes, managing pull requests, and interacting with repositories.*

**Repository Management:**
- `list_repositories`: Lists all accessible repositories
- `get_repository`: Gets details for a specific repository
- `list_branches`: Lists branches in a repository
- `list_commits`: **(Key Investigation Tool)** Lists recent commits to understand what has changed

**Content Management:**
- `get_file_content`: **(Key Investigation Tool)** Reads the content of a file to inspect a specific change
- `create_or_update_file`: Creates a new file or updates an existing one (for automated hotfixes)

**Pull Requests:**
- `list_pull_requests`: Lists pull requests
- `create_pull_request`: Creates a new pull request for a proposed fix
- `merge_pull_request`: Merges a pull request after approval

**Issues & Search:**
- `list_issues`, `create_issue`, `update_issue`: Manage repository issues
- `search_repositories`, `search_issues`: Search across GitHub

**Workflows & Actions:**
- `list_workflow_runs`, `trigger_workflow`, `cancel_workflow_run`: Manage GitHub Actions

### Infrastructure & Runtime

#### Kubernetes (`k8s_*`)
*Use for inspecting and managing runtime resources like pods, services, and deployments.*

**Workload Inspection:**
- `list_k8s_pods`: **(Primary Investigation Tool)** Lists pods, showing their status, IP, and namespace
- `get_k8s_pod_logs`: **(Primary Investigation Tool)** Gets logs from a specific pod to find runtime errors
- `list_k8s_deployments`: Lists deployments and shows their replica status
- `list_k8s_services`, `get_k8s_service`: Inspect service configurations and endpoints

**Workload Management:**
- `scale_k8s_deployment`: **(Remediation Tool)** Scales a deployment to a specific number of replicas
- `delete_k8s_pod`: **(Remediation Tool)** Deletes a pod, allowing the ReplicaSet to restart it

**Cluster & Config Inspection:**
- `list_k8s_nodes`: Checks the status, roles, and versions of cluster nodes
- `list_k8s_configmaps`, `list_k8s_secrets`: Lists configuration and secret objects

#### PowerShell (`powershell_*`)
*Use for interacting with local filesystems, Git, and Infrastructure-as-Code tools like OpenTofu.*

- `powershell_tofu_plan`: Runs tofu plan in a directory to preview infrastructure changes
- `powershell_tofu_apply`: **(Remediation Tool)** Runs tofu apply -auto-approve to apply infrastructure changes
- `powershell_git_status`: Runs git status to check the state of a local repository clone

```json
{
  "tool_name": "name_of_the_tool",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

---

**Remember**: You are a systematic, methodical engineer. Always justify your actions, verify your assumptions, and prioritize system stability above all else.
     """
    

def main():
    """Main function to initialize and run the DevOps agent."""
    try:
        # Setup logging
        setup_logging_from_env()
        logger.info("Starting DevOps Incident Response Agent")
        logger.info("=" * 50)
        
        logger.debug("Loading configuration settings")
        settings = get_settings()
        logger.info("Configuration settings loaded successfully")
        
        # Validate required settings
        logger.debug("Validating required settings")
        try:
            validate_settings()
            logger.info("All required settings are present")
        except ValueError as e:
            logger.critical(f"Settings validation failed: {e}")
            raise
        
        # Log configuration summary
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Available LLM providers: {settings.get_available_llm_providers()}")
        logger.info(f"Debug mode: {settings.debug}")
        
        # Get Slack user ID from environment
        slack_user_id = os.getenv("SLACK_USER_ID")
        if slack_user_id:
            logger.info(f"Slack user ID configured: {slack_user_id}")
        else:
            logger.warning("No Slack user ID found in environment variables")
        
        # Initialize LLM configuration
        logger.debug("Initializing LLM configuration")
        custom_config = ModelConfig(
            model_name="gemini-2.5-flash",
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.3,
            timeout=60,
            max_completion_tokens=4000,
        )
        
        try:
            gemini_25_provider = LLMFactory.create_provider(
                LLMArchitecture.GEMINI, config=custom_config
            )
            logger.info(f"LLM provider created successfully: {gemini_25_provider}")
        except LLMProviderError as e:
            logger.error(f"Failed to create LLM provider: {e}")
            raise
        
        # Get model instance
        logger.debug("Getting model instance")
        try:
            model = gemini_25_provider.get_model()
            logger.info("Model instance retrieved successfully")
        except Exception as e:
            logger.error(f"Failed to get model instance: {e}")
            raise
        
        # Load all tools
        logger.info("Loading tools...")
        
        logger.debug("Initializing GitHub toolset")
        try:
            github_config = get_github_config()
            github_toolset = GitHubToolset(
                github_token=github_config.github_personal_access_token
            )
            github_tools = github_toolset.tools
            logger.info(f"Successfully loaded {len(github_tools)} GitHub tools")
            logger.debug(f"Available GitHub tools: {[tool.name for tool in github_tools]}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub toolset: {e}")
            raise
        
        k8s_tools = load_kubernetes_tools()
        prometheus_tools = load_prometheus_tools()
        jenkins_tools = load_jenkins_tools()
        powershell_tool = load_powershell_tools()
        slack_tools = load_slack_tools()
        
        logger.info("Loading Loki tool...")
        loki_tools = [retrieve_job_logs]  # <-- FIX: Wrap the tool in a list
        validate_tools_structure(loki_tools, "Loki") # Your validation will now pass
        logger.success("Successfully loaded 1 Loki tool")
        
        logger.info("Combining all tools...")
        all_tools = []
        all_tools.extend(github_tools)
        all_tools.extend(k8s_tools)
        all_tools.extend(prometheus_tools)
        all_tools.extend(jenkins_tools)
        all_tools.extend(powershell_tool)
        all_tools.extend(slack_tools)
        all_tools.extend(loki_tools)
        
        logger.success(f"Total tools loaded: {len(all_tools)}")
        
        tool_names = [getattr(tool, "name", "Unknown") for tool in all_tools]
        logger.info(f"Tool names: {tool_names}")
        
        # Create agent prompt with Slack user ID
        logger.info("Creating agent prompt...")
        prompt = create_agent_prompt(slack_user_id)
        logger.info("Agent prompt configured")
        
        # Create memory checkpointer
        checkpointer = MemorySaver()
        logger.info("Memory checkpointer created")
        
        # Create ReAct agent
        logger.info("Creating ReAct agent...")
        devops_agent = create_react_agent(
            model=model, tools=all_tools, prompt=prompt, checkpointer=checkpointer
        )
        logger.success("DevOps ReAct agent created successfully")
        
        # Configure agent
        config = {
            "configurable": {
                "thread_id": "devops-agent-main",
                "checkpoint_id": uuid.uuid4(),
                "recursion_limit": 100
            }
        }
        
        # Interactive loop
        logger.info("=" * 50)
        logger.info("DevOps Agent is ready! Type 'quit' or 'exit' to stop.")
        if slack_user_id:
            logger.info(f"Slack integration enabled for user: {slack_user_id}")
        logger.info("=" * 50)
        
        while True:
            try:
                user_input = input("\n🔧 DevOps Agent > ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    logger.info("Shutting down DevOps Agent...")
                    break
                
                if not user_input:
                    continue
                
                logger.info(f"Processing user input: {user_input}")
                
                # Get agent response
                response = devops_agent.invoke(
                    {"messages": [{"role": "user", "content": user_input}]},
                    config=config,
                )
                
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    if hasattr(last_message, "content"):
                        print(f"\n🤖 Agent: {last_message.content}")
                    else:
                        print(f"\n🤖 Agent: {last_message}")
                else:
                    print(f"\n🤖 Agent: {response}")
            
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                print(f"❌ Error: {e}")
    
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        logger.error("Full traceback:", exc_info=True)
        return 1
    
    finally:
        logger.info("DevOps Agent shutdown complete")
        logger.info("=" * 50)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)