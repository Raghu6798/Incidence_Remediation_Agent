# In protocols/mcp/server.py

import os
from dotenv import load_dotenv
from rich import print
import sys
from typing import List, Dict, Any, Optional

# --- Framework Imports ---
from fastmcp import FastMCP

# --- Local Project Imports ---
from tools.github.github_tool import (
    GitHubAPIClient,
    ListRepositoriesTool,
    GetRepositoryTool,
    ListIssuesTool,
    CreateIssueTool,
    UpdateIssueTool,
    ListPullRequestsTool,
    CreatePullRequestTool,
    MergePullRequestTool,
    ListWorkflowRunsTool,
    TriggerWorkflowTool,
    CancelWorkflowRunTool,
    ListCommitsTool,
    ListBranchesTool,
    ListDeploymentsTool,
    CreateDeploymentTool,
    GetFileContentTool,
    CreateOrUpdateFileTool,
    ListWebhooksTool,
    CreateWebhookTool,
    SearchRepositoriesTool,
    SearchIssuesTool,
)

# --- Initialization ---
print("[bold green]Initializing GitHub DevOps MCP Server...[/bold green]")

# 1. Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
if not GITHUB_TOKEN:
    print("[bold red]FATAL: GITHUB_PERSONAL_ACCESS_TOKEN not set.[/bold red]")
    exit(1)

# 2. Create a single, shared GitHubAPIClient instance
try:
    github_client = GitHubAPIClient(token=GITHUB_TOKEN)
    print("✅ [bold]GitHub API Client[/bold] initialized.")
except Exception as e:
    print(f"[bold red]Error initializing GitHubAPIClient: {e}[/bold red]")
    exit(1)

# 3. Create the FastMCP server instance
mcp = FastMCP(
    name="GitHub DevOps MCP",
    instructions="A Model Context Protocol server providing tools for interacting with the GitHub API. Use these tools for incident response, code investigation, and managing repositories.",
)
print(f"✅ [bold]FastMCP Server '{mcp.name}'[/bold] created.")

print("\n[bold]Registering tools with the MCP server:[/bold]")

# --- MANUAL TOOL REGISTRATION ---

# Note: The tool registration logic remains the same.


@mcp.tool(
    name="list_repositories", description="List repositories for a user or organization"
)
async def list_repositories(owner: str, repo_type: str = "all", per_page: int = 30):
    tool = ListRepositoriesTool(github_client=github_client)
    return await tool._arun(owner=owner, repo_type=repo_type, per_page=per_page)


@mcp.tool(
    name="get_repository",
    description="Get detailed information about a specific repository",
)
async def get_repository(owner: str, repo: str):
    tool = GetRepositoryTool(github_client=github_client)
    return await tool._arun(owner=owner, repo=repo)


@mcp.tool(
    name="list_issues", description="List issues in a repository with filtering options"
)
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str = "",
    assignee: str = "",
    per_page: int = 30,
):
    tool = ListIssuesTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        state=state,
        labels=labels,
        assignee=assignee,
        per_page=per_page,
    )


@mcp.tool(name="create_issue", description="Create a new issue in a repository")
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
):
    tool = CreateIssueTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        title=title,
        body=body,
        labels=labels or [],
        assignees=assignees or [],
    )


@mcp.tool(name="update_issue", description="Update an existing issue")
async def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str = "",
    body: str = "",
    state: str = "",
    labels: Optional[List[str]] = None,
):
    tool = UpdateIssueTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        title=title,
        body=body,
        state=state,
        labels=labels or [],
    )


@mcp.tool(name="list_pull_requests", description="List pull requests in a repository")
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    base: str = "",
    head: str = "",
    per_page: int = 30,
):
    tool = ListPullRequestsTool(github_client=github_client)
    return await tool._arun(
        owner=owner, repo=repo, state=state, base=base, head=head, per_page=per_page
    )


@mcp.tool(name="create_pull_request", description="Create a new pull request")
async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
):
    tool = CreatePullRequestTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        title=title,
        head=head,
        base=base,
        body=body,
        draft=draft,
    )


@mcp.tool(name="merge_pull_request", description="Merge a pull request")
async def merge_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    commit_title: str = "",
    commit_message: str = "",
    merge_method: str = "merge",
):
    tool = MergePullRequestTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        commit_title=commit_title,
        commit_message=commit_message,
        merge_method=merge_method,
    )


@mcp.tool(name="list_workflow_runs", description="List workflow runs for a repository")
async def list_workflow_runs(
    owner: str,
    repo: str,
    workflow_id: str = "",
    branch: str = "",
    status: str = "",
    per_page: int = 30,
):
    tool = ListWorkflowRunsTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        workflow_id=workflow_id,
        branch=branch,
        status=status,
        per_page=per_page,
    )


@mcp.tool(name="trigger_workflow", description="Trigger a workflow dispatch event")
async def trigger_workflow(
    owner: str,
    repo: str,
    workflow_id: str,
    ref: str,
    inputs: Optional[Dict[str, Any]] = None,
):
    tool = TriggerWorkflowTool(github_client=github_client)
    return await tool._arun(
        owner=owner, repo=repo, workflow_id=workflow_id, ref=ref, inputs=inputs or {}
    )


@mcp.tool(name="cancel_workflow_run", description="Cancel a workflow run")
async def cancel_workflow_run(owner: str, repo: str, run_id: int):
    tool = CancelWorkflowRunTool(github_client=github_client)
    return await tool._arun(owner=owner, repo=repo, run_id=run_id)


@mcp.tool(name="list_commits", description="List commits in a repository")
async def list_commits(
    owner: str,
    repo: str,
    sha: str = "",
    path: str = "",
    author: str = "",
    since: str = "",
    until: str = "",
    per_page: int = 30,
):
    tool = ListCommitsTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        sha=sha,
        path=path,
        author=author,
        since=since,
        until=until,
        per_page=per_page,
    )


@mcp.tool(name="list_branches", description="List branches in a repository")
async def list_branches(
    owner: str, repo: str, protected: bool = False, per_page: int = 30
):
    tool = ListBranchesTool(github_client=github_client)
    return await tool._arun(
        owner=owner, repo=repo, protected=protected, per_page=per_page
    )


@mcp.tool(name="list_deployments", description="List deployments for a repository")
async def list_deployments(
    owner: str,
    repo: str,
    sha: str = "",
    ref: str = "",
    task: str = "",
    environment: str = "",
    per_page: int = 30,
):
    tool = ListDeploymentsTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        sha=sha,
        ref=ref,
        task=task,
        environment=environment,
        per_page=per_page,
    )


@mcp.tool(name="create_deployment", description="Create a new deployment")
async def create_deployment(
    owner: str,
    repo: str,
    ref: str,
    task: str = "deploy",
    auto_merge: bool = True,
    required_contexts: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    environment: str = "production",
    description: str = "",
):
    tool = CreateDeploymentTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        ref=ref,
        task=task,
        auto_merge=auto_merge,
        required_contexts=required_contexts or [],
        payload=payload or {},
        environment=environment,
        description=description,
    )


@mcp.tool(
    name="get_file_content", description="Get the content of a file from a repository"
)
async def get_file_content(owner: str, repo: str, path: str, ref: str = ""):
    tool = GetFileContentTool(github_client=github_client)
    return await tool._arun(owner=owner, repo=repo, path=path, ref=ref)


@mcp.tool(
    name="create_or_update_file", description="Create or update a file in a repository"
)
async def create_or_update_file(
    owner: str,
    repo: str,
    path: str,
    message: str,
    content: str,
    sha: str = "",
    branch: str = "",
    committer_name: str = "",
    committer_email: str = "",
):
    tool = CreateOrUpdateFileTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        path=path,
        message=message,
        content=content,
        sha=sha,
        branch=branch,
        committer_name=committer_name,
        committer_email=committer_email,
    )


@mcp.tool(name="list_webhooks", description="List webhooks for a repository")
async def list_webhooks(owner: str, repo: str, per_page: int = 30):
    tool = ListWebhooksTool(github_client=github_client)
    return await tool._arun(owner=owner, repo=repo, per_page=per_page)


@mcp.tool(name="create_webhook", description="Create a webhook for a repository")
async def create_webhook(
    owner: str,
    repo: str,
    url: str,
    events: Optional[List[str]] = None,
    active: bool = True,
    secret: str = "",
):
    tool = CreateWebhookTool(github_client=github_client)
    return await tool._arun(
        owner=owner,
        repo=repo,
        url=url,
        events=events or ["push"],
        active=active,
        secret=secret,
    )


@mcp.tool(name="search_repositories", description="Search for repositories on GitHub")
async def search_repositories(
    query: str, sort: str = "", order: str = "desc", per_page: int = 30
):
    tool = SearchRepositoriesTool(github_client=github_client)
    return await tool._arun(query=query, sort=sort, order=order, per_page=per_page)


@mcp.tool(
    name="search_issues", description="Search for issues and pull requests on GitHub"
)
async def search_issues(
    query: str, sort: str = "", order: str = "desc", per_page: int = 30
):
    tool = SearchIssuesTool(github_client=github_client)
    return await tool._arun(query=query, sort=sort, order=order, per_page=per_page)


print("\n[bold green]All tools registered successfully.[/bold green]")

# --- Main Execution Block (for SSE Transport) ---
if __name__ == "__main__":
    # Get host and port from environment variables, with sensible defaults
    MCP_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    MCP_PORT = int(os.getenv("MCP_SERVER_PORT", "8000"))

    print(
        f"🚀 Starting GitHub DevOps MCP Server in SSE mode on http://{MCP_HOST}:{MCP_PORT}"
    )
    print("   The SSE endpoint will be at /sse/")
    print("   Press Ctrl+C to stop the server.")

    # Run the server using SSE transport
    mcp.run(
        transport="sse",
        host=MCP_HOST,
        port=MCP_PORT,
    )
