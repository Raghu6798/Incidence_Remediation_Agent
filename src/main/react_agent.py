#!/usr/bin/env python3
"""
DevOps Incident Response Agent - Main Script
This script initializes and runs the ReAct agent with all required tools.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from loguru import logger
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from src.utils.logging_config import setup_logging_from_env
from src.config.settings import Settings

from llms.factory import LLMFactory, LLMType
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
from tools.prometheus.factory import PrometheusToolBuilder,PrometheusToolsetFactory

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
        
        if not hasattr(tool, 'name'):
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


def create_agent_prompt() -> str:
    """Create the system prompt for the DevOps agent."""
    return """You are a DevOps Incident Response Agent. Your role is to help diagnose, troubleshoot, and resolve infrastructure and application issues.

Available Tools:
- GitHub tools: For repository management, issue tracking, and code analysis
- Kubernetes tools: For container orchestration, pod management, and cluster operations
- Prometheus tools: For metrics collection, monitoring, and alerting

Guidelines:
1. Always gather information before taking action
2. Use appropriate tools based on the incident type
3. Provide clear explanations for your actions
4. Suggest preventive measures when applicable
5. Document your findings and solutions

When responding to incidents:
1. Assess the situation using monitoring tools
2. Identify affected components
3. Implement appropriate remediation steps
4. Verify the resolution
5. Provide a summary of actions taken

Be helpful, thorough, and prioritize system stability and security."""


def main():
    """Main function to initialize and run the DevOps agent."""
    try:
        # Setup logging
        setup_logging_from_env()
        logger.info("Starting DevOps Incident Response Agent")
        logger.info("=" * 50)
        
        # Create LLM provider and model
        logger.info("Creating LLM provider...")
        
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
        logger.info(
            f"Available LLM providers: {settings.get_available_llm_providers()}"
        )
        logger.info(f"Debug mode: {settings.debug}")

        # Initialize LLM configuration
        logger.debug("Initializing LLM configuration")
        llm_config = get_llm_config()

        # Use the first available LLM provider
        available_providers = settings.get_available_llm_providers()
        if not available_providers:
            raise ValueError(
                "No LLM providers configured. Please set at least one API key."
            )

        # For now, use Gemini as default if available, otherwise use the first available
        if "gemini" in available_providers and llm_config.google_api_key:
            provider_type = LLMType.GEMINI
            api_key = llm_config.google_api_key
            model_name = llm_config.default_model
        else:
            # Use the first available provider
            provider_type = LLMType(available_providers[0])
            if provider_type == LLMType.GEMINI:
                api_key = llm_config.google_api_key
            elif provider_type == LLMType.OPENAI:
                api_key = llm_config.openrouter_api_key
            elif provider_type == LLMType.CLAUDE:
                api_key = llm_config.claude_api_key
            elif provider_type == LLMType.LLAMA:
                api_key = llm_config.cerebras_api_key
            elif provider_type == LLMType.MISTRAL:
                api_key = llm_config.mistral_api_key
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")

            model_name = llm_config.default_model

        zlm_config = ModelConfig(
            model_name=model_name,
            api_key=api_key,
            temperature=llm_config.default_temperature,
            max_tokens=llm_config.default_max_tokens,
            timeout=llm_config.default_timeout,
        )
        logger.info(
            f"LLM configuration created for {provider_type.value} model: {zlm_config.model_name}"
        )

        logger.debug(f"Creating LLM provider for type: {provider_type.value}")
        try:
            glm_provider = LLMFactory.create_provider(provider_type, config=zlm_config)
            logger.info(f"LLM provider created successfully: {glm_provider}")
        except LLMProviderError as e:
            logger.error(f"Failed to create LLM provider: {e}")
            raise

        # Get model instance
        logger.debug("Getting model instance")
        try:
            model = glm_provider.get_model()
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
        
        # Load Kubernetes tools
        k8s_tools = load_kubernetes_tools()
        
        # Load Prometheus tools - FIXED: Use the function instead of direct builder
        prometheus_tools = load_prometheus_tools()  # This returns a list
        
        logger.debug(f"Prometheus tools loaded: {[tool.name for tool in prometheus_tools]}")
        
        # Combine all tools into a flat list
        logger.info("Combining all tools...")
        all_tools = []
        all_tools.extend(github_tools)     
        all_tools.extend(k8s_tools)         
        all_tools.extend(prometheus_tools)  # Now this works correctly
        
        # Final validation of combined tools
        validate_tools_structure(all_tools, "Combined")
        
        logger.success(f"Total tools loaded: {len(all_tools)}")
        
        # Log tool names for verification
        tool_names = [getattr(tool, 'name', 'Unknown') for tool in all_tools]
        logger.info(f"Tool names: {tool_names}")
        
        # Create agent prompt
        logger.info("Creating agent prompt...")
        prompt = create_agent_prompt()
        logger.info("Agent prompt configured")
        
        # Create memory checkpointer
        checkpointer = MemorySaver()
        logger.info("Memory checkpointer created")
        
        # Create ReAct agent
        logger.info("Creating ReAct agent...")
        devops_agent = create_react_agent(
            model=model,
            tools=all_tools,
            prompt=prompt,
            checkpointer=checkpointer
        )
        logger.success("DevOps ReAct agent created successfully")
        
        # Configure agent
        config = {
            "configurable": {
                "thread_id": "devops-agent-main",
                "checkpoint_id": None,
            }
        }
        
        # Interactive loop
        logger.info("=" * 50)
        logger.info("DevOps Agent is ready! Type 'quit' or 'exit' to stop.")
        logger.info("=" * 50)
        
        while True:
            try:
                user_input = input("\n🔧 DevOps Agent > ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("Shutting down DevOps Agent...")
                    break
                
                if not user_input:
                    continue
                
                logger.info(f"Processing user input: {user_input}")
                
                # Get agent response
                response = devops_agent.invoke(
                    {"messages": [{"role": "user", "content": user_input}]},
                    config=config
                )
                
                # Extract and display the response
                if response and "messages" in response:
                    last_message = response["messages"][-1]
                    if hasattr(last_message, 'content'):
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