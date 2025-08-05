import os
from dotenv import load_dotenv

from llms.factory import LLMFactory, LLMType
from llms.base import ModelConfig
from langgraph.prebuilt import create_react_agent

from DevOps_Agent.tools.github.factory import GitHubToolset

load_dotenv()


if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY not found in environment variables.")
if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
    raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN not found in environment variables.")

zlm_config = ModelConfig(
    model_name="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
)
glm_provider = LLMFactory.create_provider(LLMType.GEMINI, config=zlm_config)
model = glm_provider.get_model()


github_toolset = GitHubToolset(github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))

github_tools = github_toolset.tools
print(f"Successfully loaded {len(github_tools)} GitHub tools.")


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

# Create the ReAct agent, passing in the model and your list of GitHub tools
devops_agent = create_react_agent(model=model, tools=github_tools, prompt=agent_prompt)

while True:
    query = input("Hey what is up : ")
    if query.lower() == "quit":
        break
    response = devops_agent.invoke({"messages": [("user", query)]})
    print("\n--- Agent's Final Response ---")
    print(response["messages"][-1].content)
