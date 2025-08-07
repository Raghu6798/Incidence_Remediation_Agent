import os
import sys
from typing import Dict, Any

from llms.factory import LLMFactory, LLMType
from llms.base import ModelConfig, LLMProviderError
from langgraph.prebuilt import create_react_agent

from tools.github.factory import GitHubToolset
from src.utils.logging_config import setup_logging_from_env, get_logger
from src.config.settings import (
    get_settings,
    validate_settings,
    get_llm_config,
    get_github_config,
)

# Setup logging first
setup_logging_from_env()
logger = get_logger(__name__)


def main():
    """Main function to run the DevOps agent with comprehensive logging."""

    logger.info("Starting DevOps Incident Response Agent")
    logger.info("=" * 50)

    try:
        # Load and validate settings using Pydantic
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

        # Create LLM provider
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

        # Initialize GitHub toolset
        logger.debug("Initializing GitHub toolset")
        try:
            github_config = get_github_config()
            github_toolset = GitHubToolset(
                github_token=github_config.github_personal_access_token
            )
            github_tools = github_toolset.tools
            logger.info(f"Successfully loaded {len(github_tools)} GitHub tools")
            logger.debug(f"Available tools: {[tool.name for tool in github_tools]}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub toolset: {e}")
            raise

        # Define agent prompt
        logger.debug("Setting up agent prompt")
        agent_prompt = """
You are an expert DevOps and Incident Response agent.
Your primary goal is to help users diagnose and resolve issues by interacting with GitHub.

You have access to a suite of tools that can:
- List repositories, commits, pull requests, and issues.
- Read the content of files in a repository.
- Check the status of GitHub Actions workflows.
- Create new issues and pull requests.
- Trigger and cancel workflows.

When a user asks a question, break it down into steps.
For each step, decide which tool is the most appropriate to use.
Execute the tool, observe the result, and use that information to decide the next step.
Continue this process until you have enough information to answer the user's question.
"""
        logger.info("Agent prompt configured")

        # Create the ReAct agent
        logger.debug("Creating ReAct agent")
        try:
            devops_agent = create_react_agent(
                model=model, tools=github_tools, prompt=agent_prompt
            )
            logger.info("ReAct agent created successfully")
        except Exception as e:
            logger.error(f"Failed to create ReAct agent: {e}")
            raise

        # Main interaction loop
        logger.info("Starting agent interaction loop")
        logger.info("Type 'quit' to exit the agent")
        logger.info("-" * 50)

        session_count = 0
        while True:
            try:
                session_count += 1
                logger.info(f"Session {session_count}: Waiting for user input")

                query = input("Hey what is up : ").strip()

                if not query:
                    logger.warning("Empty query received, continuing...")
                    continue

                if query.lower() == "quit":
                    logger.info("User requested to quit the agent")
                    break

                logger.info(
                    f"Processing query: {query}{'...' if len(query) > 100 else ''}"
                )
                logger.debug(f"Full query: {query}")

                # Invoke agent
                logger.debug("Invoking agent with query")
                try:
                    response = devops_agent.invoke({"messages": [("user", query)]})
                    logger.info("Agent response generated successfully")

                    # Extract final response
                    final_response = response["messages"][-1].content
                    logger.debug(
                        f"Final response length: {len(final_response)} characters"
                    )

                    # Display response
                    print("\n--- Agent's Final Response ---")
                    print(final_response)
                    print("-" * 50)

                    logger.success(f"Session {session_count} completed successfully")

                except Exception as e:
                    logger.error(f"Error during agent invocation: {e}")
                    logger.exception("Full traceback:")
                    print(f"\nError: {e}")
                    print("Please try again or contact support if the issue persists.")

            except KeyboardInterrupt:
                logger.warning("Keyboard interrupt received")
                print("\nInterrupted by user. Exiting...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                logger.exception("Full traceback:")
                print(f"\nUnexpected error: {e}")
                print("Please try again or contact support if the issue persists.")

        logger.info(f"Agent session ended. Total sessions processed: {session_count}")

    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        logger.exception("Full traceback:")
        print(f"\nCritical error: {e}")
        sys.exit(1)

    finally:
        logger.info("DevOps Agent shutdown complete")
        logger.info("=" * 50)


if __name__ == "__main__":
    main()
