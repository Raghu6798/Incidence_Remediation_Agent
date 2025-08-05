import os
from dotenv import load_dotenv
from tools.github.github_tool import (
    GitHubAPIClient,
    GetRepositoryTool,
    ListRepositoriesTool,
    ListIssuesTool,
    CreateIssueTool,
    UpdateIssueTool,
    ListPullRequestsTool,
    SearchIssuesTool,
    SearchRepositoriesTool,
    ListWebhooksTool,
    CreateDeploymentTool,
    ListDeploymentsTool,
    ListBranchesTool,
    CreateWebhookTool,
    TriggerWorkflowTool,
    CreateOrUpdateFileTool,
    ListCommitsTool,
    CancelWorkflowRunTool,
    CreatePullRequestTool,
    MergePullRequestTool,
    ListWorkflowRunsTool,
    GetFileContentTool,
)
from tools.base import AbstractTool
from typing import Optional, List

load_dotenv()


class GitHubToolset:
    """Factory class to create and manage all GitHub tools."""

    def __init__(self, github_token: str):
        self.client = GitHubAPIClient(token=github_token)
        self._tools = None

    @property
    def tools(self) -> List[AbstractTool]:
        """Get all available GitHub tools."""
        if self._tools is None:
            self._tools = [
                # Repository Management
                ListRepositoriesTool(github_client=self.client),
                GetRepositoryTool(github_client=self.client),
                # Issues Management
                ListIssuesTool(github_client=self.client),
                CreateIssueTool(github_client=self.client),
                UpdateIssueTool(github_client=self.client),
                # Pull Requests Management
                ListPullRequestsTool(github_client=self.client),
                CreatePullRequestTool(github_client=self.client),
                MergePullRequestTool(github_client=self.client),
                # Workflows and Actions
                ListWorkflowRunsTool(github_client=self.client),
                TriggerWorkflowTool(github_client=self.client),
                CancelWorkflowRunTool(github_client=self.client),
                # Commits and Branches
                ListCommitsTool(github_client=self.client),
                ListBranchesTool(github_client=self.client),
                # Deployments
                ListDeploymentsTool(github_client=self.client),
                CreateDeploymentTool(github_client=self.client),
                # Repository Content
                GetFileContentTool(github_client=self.client),
                CreateOrUpdateFileTool(github_client=self.client),
                # Webhooks
                ListWebhooksTool(github_client=self.client),
                CreateWebhookTool(github_client=self.client),
                # Search
                SearchRepositoriesTool(github_client=self.client),
                SearchIssuesTool(github_client=self.client),
            ]
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[AbstractTool]:
        """Get a specific tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tools_by_category(self, category: str) -> List[AbstractTool]:
        """Get tools by category."""
        categories = {
            "repository": ["list_repositories", "get_repository"],
            "issues": ["list_issues", "create_issue", "update_issue"],
            "pull_requests": [
                "list_pull_requests",
                "create_pull_request",
                "merge_pull_request",
            ],
            "workflows": [
                "list_workflow_runs",
                "trigger_workflow",
                "cancel_workflow_run",
            ],
            "commits": ["list_commits", "list_branches"],
            "deployments": ["list_deployments", "create_deployment"],
            "content": ["get_file_content", "create_or_update_file"],
            "webhooks": ["list_webhooks", "create_webhook"],
            "search": ["search_repositories", "search_issues"],
        }

        tool_names = categories.get(category, [])
        return [tool for tool in self.tools if tool.name in tool_names]


# ============= USAGE EXAMPLE =============
def example_usage():
    """Example of how to use the GitHub toolset."""

    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        print("Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable not set.")
        return None

    toolset = GitHubToolset(github_token=github_token)

    repo_tool = toolset.get_tool_by_name("get_repository")

    if repo_tool:
        print("Attempting to get repository 'Hello-World' from 'octocat'...")
        try:
            # CORRECTED LINE: Pass a single dictionary as the tool_input
            tool_input = {"owner": "octocat", "repo": "Hello-World"}
            result = repo_tool.run(tool_input)

            print("Result from get_repository tool:")
            # Pretty print the result if it's a dictionary
            if isinstance(result, dict):
                import json

                print(json.dumps(result, indent=2))
            else:
                print(result)

        except Exception as e:
            print(f"An error occurred while running the tool: {e}")

    else:
        print("get_repository tool not found.")

    return toolset


if __name__ == "__main__":
    toolset = example_usage()
    if toolset:
        print(f"\nAvailable tools: {[tool.name for tool in toolset.tools]}")
    print(toolset.get_tools_by_category())
