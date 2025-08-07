from ..base import AbstractTool
from typing import Dict, Any, Optional, List, Type
import aiohttp
import requests
from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

class GitHubAPIClient:
    """Centralized GitHub API client with authentication."""

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }

    def make_request(
        self, method: str, endpoint: str, data: Dict[Any, Any] = None
    ) -> Dict[Any, Any]:
        """Make synchronous HTTP request to GitHub API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return response.json() if response.content else {"status": "success"}

        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None),
            }

    async def make_async_request(
        self, method: str, endpoint: str, data: Dict[Any, Any] = None
    ) -> Dict[Any, Any]:
        """Make asynchronous HTTP request to GitHub API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(
                        url, headers=self.headers, params=data
                    ) as response:
                        response.raise_for_status()
                        result = (
                            await response.json()
                            if response.content_length
                            else {"status": "success"}
                        )
                elif method.upper() == "POST":
                    async with session.post(
                        url, headers=self.headers, json=data
                    ) as response:
                        response.raise_for_status()
                        result = (
                            await response.json()
                            if response.content_length
                            else {"status": "success"}
                        )
                elif method.upper() == "PATCH":
                    async with session.patch(
                        url, headers=self.headers, json=data
                    ) as response:
                        response.raise_for_status()
                        result = (
                            await response.json()
                            if response.content_length
                            else {"status": "success"}
                        )
                elif method.upper() == "PUT":
                    async with session.put(
                        url, headers=self.headers, json=data
                    ) as response:
                        response.raise_for_status()
                        result = (
                            await response.json()
                            if response.content_length
                            else {"status": "success"}
                        )
                elif method.upper() == "DELETE":
                    async with session.delete(url, headers=self.headers) as response:
                        response.raise_for_status()
                        result = (
                            {"status": "success"}
                            if response.status == 204
                            else await response.json()
                        )
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}

                return result

        except Exception as e:
            return {"error": str(e)}


# ============= REPOSITORY MANAGEMENT TOOLS =============
class ListRepositoriesInput(BaseModel):
    owner: str = Field(description="GitHub username or organization name")
    repo_type: str = Field(
        default="all",
        description="Type of repos: 'all', 'owner', 'public', 'private', 'member'",
    )
    per_page: int = Field(
        default=30, description="Number of repositories per page (max 100)"
    )


class ListRepositoriesTool(AbstractTool):
    name: str = "list_repositories"
    description: str = "List repositories for a user or organization"
    args_schema: Type[BaseModel] = ListRepositoriesInput
    github_client: GitHubAPIClient  # <--- DECLARE THE FIELD

    def _run(
        self,
        owner: str,
        repo_type: str = "all",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"users/{owner}/repos"
        params = {"type": repo_type, "per_page": per_page, "sort": "updated"}
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo_type: str = "all",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"users/{owner}/repos"
        params = {"type": repo_type, "per_page": per_page, "sort": "updated"}
        return await self.github_client.make_async_request("GET", endpoint, params)


class GetRepositoryInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")


class GetRepositoryTool(AbstractTool):
    name: str = "get_repository"
    description: str = "Get detailed information about a specific repository"
    args_schema: Type[BaseModel] = GetRepositoryInput
    github_client: GitHubAPIClient  # <--- DECLARE THE FIELD

    def _run(
        self,
        owner: str,
        repo: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}"
        return self.github_client.make_request("GET", endpoint)

    async def _arun(
        self,
        owner: str,
        repo: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}"
        return await self.github_client.make_async_request("GET", endpoint)


# ============= ISSUES MANAGEMENT TOOLS =============
class ListIssuesInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    state: str = Field(
        default="open", description="Issue state: 'open', 'closed', 'all'"
    )
    labels: str = Field(default="", description="Comma-separated list of label names")
    assignee: str = Field(default="", description="Username of assignee")
    per_page: int = Field(default=30, description="Number of issues per page")


class ListIssuesTool(AbstractTool):
    name: str = "list_issues"
    description: str = "List issues in a repository with filtering options"
    args_schema: Type[BaseModel] = ListIssuesInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = "",
        assignee: str = "",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": per_page, "sort": "updated"}
        if labels:
            params["labels"] = labels
        if assignee:
            params["assignee"] = assignee
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = "",
        assignee: str = "",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": per_page, "sort": "updated"}
        if labels:
            params["labels"] = labels
        if assignee:
            params["assignee"] = assignee
        return await self.github_client.make_async_request("GET", endpoint, params)


class CreateIssueInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    title: str = Field(description="Issue title")
    body: str = Field(default="", description="Issue description/body")
    labels: List[str] = Field(default=[], description="List of label names")
    assignees: List[str] = Field(default=[], description="List of usernames to assign")


class CreateIssueTool(AbstractTool):
    name: str = "create_issue"
    description: str = "Create a new issue in a repository"
    args_schema: Type[BaseModel] = CreateIssueInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: List[str] = None,
        assignees: List[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues"
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        return self.github_client.make_request("POST", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: List[str] = None,
        assignees: List[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues"
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        return await self.github_client.make_async_request("POST", endpoint, data)


class UpdateIssueInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    issue_number: int = Field(description="Issue number")
    title: str = Field(default="", description="New issue title")
    body: str = Field(default="", description="New issue body")
    state: str = Field(default="", description="Issue state: 'open' or 'closed'")
    labels: List[str] = Field(default=[], description="List of label names")


class UpdateIssueTool(AbstractTool):
    name: str = "update_issue"
    description: str = "Update an existing issue"
    args_schema: Type[BaseModel] = UpdateIssueInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        labels: List[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues/{issue_number}"
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels
        return self.github_client.make_request("PATCH", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        labels: List[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/issues/{issue_number}"
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels
        return await self.github_client.make_async_request("PATCH", endpoint, data)


# ============= PULL REQUESTS MANAGEMENT TOOLS =============
class ListPullRequestsInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    state: str = Field(default="open", description="PR state: 'open', 'closed', 'all'")
    base: str = Field(default="", description="Base branch name")
    head: str = Field(default="", description="Head branch name")
    per_page: int = Field(default=30, description="Number of PRs per page")


class ListPullRequestsTool(AbstractTool):
    name: str = "list_pull_requests"
    description: str = "List pull requests in a repository"
    args_schema: Type[BaseModel] = ListPullRequestsInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        base: str = "",
        head: str = "",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": per_page, "sort": "updated"}
        if base:
            params["base"] = base
        if head:
            params["head"] = head
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        base: str = "",
        head: str = "",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls"
        params = {"state": state, "per_page": per_page, "sort": "updated"}
        if base:
            params["base"] = base
        if head:
            params["head"] = head
        return await self.github_client.make_async_request("GET", endpoint, params)


class CreatePullRequestInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    title: str = Field(description="Pull request title")
    head: str = Field(description="Branch name containing changes")
    base: str = Field(description="Branch name to merge into")
    body: str = Field(default="", description="Pull request description")
    draft: bool = Field(default=False, description="Create as draft PR")


class CreatePullRequestTool(AbstractTool):
    name: str = "create_pull_request"
    description: str = "Create a new pull request"
    args_schema: Type[BaseModel] = CreatePullRequestInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        return self.github_client.make_request("POST", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        return await self.github_client.make_async_request("POST", endpoint, data)


class MergePullRequestInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    pull_number: int = Field(description="Pull request number")
    commit_title: str = Field(default="", description="Commit title for merge")
    commit_message: str = Field(default="", description="Commit message for merge")
    merge_method: str = Field(
        default="merge", description="Merge method: 'merge', 'squash', 'rebase'"
    )


class MergePullRequestTool(AbstractTool):
    name: str = "merge_pull_request"
    description: str = "Merge a pull request"
    args_schema: Type[BaseModel] = MergePullRequestInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: str = "",
        commit_message: str = "",
        merge_method: str = "merge",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls/{pull_number}/merge"
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        return self.github_client.make_request("PUT", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: str = "",
        commit_message: str = "",
        merge_method: str = "merge",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/pulls/{pull_number}/merge"
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        return await self.github_client.make_async_request("PUT", endpoint, data)


# ... (The rest of the file follows the same pattern) ...
# I will apply the fix to all classes below for completeness.


# ============= WORKFLOWS AND ACTIONS TOOLS =============
class ListWorkflowRunsInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    workflow_id: str = Field(default="", description="Workflow ID or filename")
    branch: str = Field(default="", description="Branch name to filter runs")
    status: str = Field(
        default="", description="Run status: 'completed', 'in_progress', 'queued'"
    )
    per_page: int = Field(default=30, description="Number of runs per page")


class ListWorkflowRunsTool(AbstractTool):
    name: str = "list_workflow_runs"
    description: str = "List workflow runs for a repository"
    args_schema: Type[BaseModel] = ListWorkflowRunsInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        workflow_id: str = "",
        branch: str = "",
        status: str = "",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        if workflow_id:
            endpoint = f"repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"repos/{owner}/{repo}/actions/runs"

        params = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        if status:
            params["status"] = status

        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        workflow_id: str = "",
        branch: str = "",
        status: str = "",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        if workflow_id:
            endpoint = f"repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        else:
            endpoint = f"repos/{owner}/{repo}/actions/runs"

        params = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        if status:
            params["status"] = status

        return await self.github_client.make_async_request("GET", endpoint, params)


class TriggerWorkflowInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    workflow_id: str = Field(description="Workflow ID or filename")
    ref: str = Field(description="Git reference (branch/tag)")
    inputs: Dict[str, Any] = Field(default={}, description="Workflow inputs")


class TriggerWorkflowTool(AbstractTool):
    name: str = "trigger_workflow"
    description: str = "Trigger a workflow dispatch event"
    args_schema: Type[BaseModel] = TriggerWorkflowInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: Dict[str, Any] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
        data = {"ref": ref}
        if inputs:
            data["inputs"] = inputs
        return self.github_client.make_request("POST", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: Dict[str, Any] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
        data = {"ref": ref}
        if inputs:
            data["inputs"] = inputs
        return await self.github_client.make_async_request("POST", endpoint, data)


class CancelWorkflowRunInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    run_id: int = Field(description="Workflow run ID")


class CancelWorkflowRunTool(AbstractTool):
    name: str = "cancel_workflow_run"
    description: str = "Cancel a workflow run"
    args_schema: Type[BaseModel] = CancelWorkflowRunInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        run_id: int,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
        return self.github_client.make_request("POST", endpoint)

    async def _arun(
        self,
        owner: str,
        repo: str,
        run_id: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
        return await self.github_client.make_async_request("POST", endpoint)


# ============= COMMITS AND BRANCHES TOOLS =============
class ListCommitsInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    sha: str = Field(
        default="", description="SHA or branch to start listing commits from"
    )
    path: str = Field(default="", description="Only commits containing this file path")
    author: str = Field(default="", description="GitHub login or email address")
    since: str = Field(default="", description="ISO 8601 date: YYYY-MM-DDTHH:MM:SSZ")
    until: str = Field(default="", description="ISO 8601 date: YYYY-MM-DDTHH:MM:SSZ")
    per_page: int = Field(default=30, description="Number of commits per page")


class ListCommitsTool(AbstractTool):
    name: str = "list_commits"
    description: str = "List commits in a repository"
    args_schema: Type[BaseModel] = ListCommitsInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        sha: str = "",
        path: str = "",
        author: str = "",
        since: str = "",
        until: str = "",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/commits"
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        sha: str = "",
        path: str = "",
        author: str = "",
        since: str = "",
        until: str = "",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/commits"
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if author:
            params["author"] = author
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        return await self.github_client.make_async_request("GET", endpoint, params)


class ListBranchesInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    protected: bool = Field(default=False, description="Filter by protection status")
    per_page: int = Field(default=30, description="Number of branches per page")


class ListBranchesTool(AbstractTool):
    name: str = "list_branches"
    description: str = "List branches in a repository"
    args_schema: Type[BaseModel] = ListBranchesInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        protected: bool = False,
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/branches"
        params = {"per_page": per_page}
        if protected:
            params["protected"] = "true"
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        protected: bool = False,
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/branches"
        params = {"per_page": per_page}
        if protected:
            params["protected"] = "true"
        return await self.github_client.make_async_request("GET", endpoint, params)


# ============= DEPLOYMENT AND ENVIRONMENTS TOOLS =============
class ListDeploymentsInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    sha: str = Field(default="", description="SHA to filter deployments")
    ref: str = Field(default="", description="Name of ref to filter deployments")
    task: str = Field(default="", description="Task to filter deployments")
    environment: str = Field(
        default="", description="Environment to filter deployments"
    )
    per_page: int = Field(default=30, description="Number of deployments per page")


class ListDeploymentsTool(AbstractTool):
    name: str = "list_deployments"
    description: str = "List deployments for a repository"
    args_schema: Type[BaseModel] = ListDeploymentsInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        sha: str = "",
        ref: str = "",
        task: str = "",
        environment: str = "",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/deployments"
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if ref:
            params["ref"] = ref
        if task:
            params["task"] = task
        if environment:
            params["environment"] = environment
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        sha: str = "",
        ref: str = "",
        task: str = "",
        environment: str = "",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/deployments"
        params = {"per_page": per_page}
        if sha:
            params["sha"] = sha
        if ref:
            params["ref"] = ref
        if task:
            params["task"] = task
        if environment:
            params["environment"] = environment
        return await self.github_client.make_async_request("GET", endpoint, params)


class CreateDeploymentInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    ref: str = Field(description="Git reference to deploy")
    task: str = Field(default="deploy", description="Task name for deployment")
    auto_merge: bool = Field(default=True, description="Auto merge default branch")
    required_contexts: List[str] = Field(
        default=[], description="Required status contexts"
    )
    payload: Dict[str, Any] = Field(default={}, description="JSON payload")
    environment: str = Field(default="production", description="Target environment")
    description: str = Field(default="", description="Deployment description")


class CreateDeploymentTool(AbstractTool):
    name: str = "create_deployment"
    description: str = "Create a new deployment"
    args_schema: Type[BaseModel] = CreateDeploymentInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        ref: str,
        task: str = "deploy",
        auto_merge: bool = True,
        required_contexts: List[str] = None,
        payload: Dict[str, Any] = None,
        environment: str = "production",
        description: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/deployments"
        data = {
            "ref": ref,
            "task": task,
            "auto_merge": auto_merge,
            "environment": environment,
        }
        if required_contexts:
            data["required_contexts"] = required_contexts
        if payload:
            data["payload"] = payload
        if description:
            data["description"] = description
        return self.github_client.make_request("POST", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        ref: str,
        task: str = "deploy",
        auto_merge: bool = True,
        required_contexts: List[str] = None,
        payload: Dict[str, Any] = None,
        environment: str = "production",
        description: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/deployments"
        data = {
            "ref": ref,
            "task": task,
            "auto_merge": auto_merge,
            "environment": environment,
        }
        if required_contexts:
            data["required_contexts"] = required_contexts
        if payload:
            data["payload"] = payload
        if description:
            data["description"] = description
        return await self.github_client.make_async_request("POST", endpoint, data)


# ============= REPOSITORY CONTENT TOOLS =============
class GetFileContentInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    path: str = Field(description="File path in repository")
    ref: str = Field(
        default="",
        description="Branch, tag, or commit SHA (defaults to default branch)",
    )


class GetFileContentTool(AbstractTool):
    name: str = "get_file_content"
    description: str = "Get the content of a file from a repository"
    args_schema: Type[BaseModel] = GetFileContentInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        return await self.github_client.make_async_request("GET", endpoint, params)


class CreateOrUpdateFileInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    path: str = Field(description="File path in repository")
    message: str = Field(description="Commit message")
    content: str = Field(description="Base64 encoded file content")
    sha: str = Field(
        default="", description="SHA of existing file (required for updates)"
    )
    branch: str = Field(
        default="", description="Branch name (defaults to default branch)"
    )
    committer_name: str = Field(default="", description="Committer name")
    committer_email: str = Field(default="", description="Committer email")


class CreateOrUpdateFileTool(AbstractTool):
    name: str = "create_or_update_file"
    description: str = "Create or update a file in a repository"
    args_schema: Type[BaseModel] = CreateOrUpdateFileInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        content: str,
        sha: str = "",
        branch: str = "",
        committer_name: str = "",
        committer_email: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        data = {"message": message, "content": content}
        if sha:
            data["sha"] = sha
        if branch:
            data["branch"] = branch
        if committer_name and committer_email:
            data["committer"] = {"name": committer_name, "email": committer_email}
        return self.github_client.make_request("PUT", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        content: str,
        sha: str = "",
        branch: str = "",
        committer_name: str = "",
        committer_email: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/contents/{path}"
        data = {"message": message, "content": content}
        if sha:
            data["sha"] = sha
        if branch:
            data["branch"] = branch
        if committer_name and committer_email:
            data["committer"] = {"name": committer_name, "email": committer_email}
        return await self.github_client.make_async_request("PUT", endpoint, data)


# ============= WEBHOOKS TOOLS =============
class ListWebhooksInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    per_page: int = Field(default=30, description="Number of webhooks per page")


class ListWebhooksTool(AbstractTool):
    name: str = "list_webhooks"
    description: str = "List webhooks for a repository"
    args_schema: Type[BaseModel] = ListWebhooksInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/hooks"
        params = {"per_page": per_page}
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/hooks"
        params = {"per_page": per_page}
        return await self.github_client.make_async_request("GET", endpoint, params)


class CreateWebhookInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")
    url: str = Field(description="Webhook URL")
    events: List[str] = Field(
        default=["push"], description="List of events to trigger webhook"
    )
    active: bool = Field(default=True, description="Whether webhook is active")
    secret: str = Field(default="", description="Webhook secret for validation")


class CreateWebhookTool(AbstractTool):
    name: str = "create_webhook"
    description: str = "Create a webhook for a repository"
    args_schema: Type[BaseModel] = CreateWebhookInput
    github_client: GitHubAPIClient

    def _run(
        self,
        owner: str,
        repo: str,
        url: str,
        events: List[str] = None,
        active: bool = True,
        secret: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/hooks"
        config = {"url": url, "content_type": "json"}
        if secret:
            config["secret"] = secret

        data = {
            "name": "web",
            "active": active,
            "events": events or ["push"],
            "config": config,
        }
        return self.github_client.make_request("POST", endpoint, data)

    async def _arun(
        self,
        owner: str,
        repo: str,
        url: str,
        events: List[str] = None,
        active: bool = True,
        secret: str = "",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = f"repos/{owner}/{repo}/hooks"
        config = {"url": url, "content_type": "json"}
        if secret:
            config["secret"] = secret

        data = {
            "name": "web",
            "active": active,
            "events": events or ["push"],
            "config": config,
        }
        return await self.github_client.make_async_request("POST", endpoint, data)


# ============= SEARCH TOOLS =============
class SearchRepositoriesInput(BaseModel):
    query: str = Field(description="Search query")
    sort: str = Field(
        default="",
        description="Sort by: 'stars', 'forks', 'help-wanted-issues', 'updated'",
    )
    order: str = Field(default="desc", description="Sort order: 'asc' or 'desc'")
    per_page: int = Field(default=30, description="Number of results per page")


class SearchRepositoriesTool(AbstractTool):
    name: str = "search_repositories"
    description: str = "Search for repositories on GitHub"
    args_schema: Type[BaseModel] = SearchRepositoriesInput
    github_client: GitHubAPIClient

    def _run(
        self,
        query: str,
        sort: str = "",
        order: str = "desc",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = "search/repositories"
        params = {"q": query, "per_page": per_page, "order": order}
        if sort:
            params["sort"] = sort
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        query: str,
        sort: str = "",
        order: str = "desc",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = "search/repositories"
        params = {"q": query, "per_page": per_page, "order": order}
        if sort:
            params["sort"] = sort
        return await self.github_client.make_async_request("GET", endpoint, params)


class SearchIssuesInput(BaseModel):
    query: str = Field(description="Search query")
    sort: str = Field(
        default="", description="Sort by: 'comments', 'reactions', 'created', 'updated'"
    )
    order: str = Field(default="desc", description="Sort order: 'asc' or 'desc'")
    per_page: int = Field(default=30, description="Number of results per page")


class SearchIssuesTool(AbstractTool):
    name: str = "search_issues"
    description: str = "Search for issues and pull requests on GitHub"
    args_schema: Type[BaseModel] = SearchIssuesInput
    github_client: GitHubAPIClient

    def _run(
        self,
        query: str,
        sort: str = "",
        order: str = "desc",
        per_page: int = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        endpoint = "search/issues"
        params = {"q": query, "per_page": per_page, "order": order}
        if sort:
            params["sort"] = sort
        return self.github_client.make_request("GET", endpoint, params)

    async def _arun(
        self,
        query: str,
        sort: str = "",
        order: str = "desc",
        per_page: int = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        endpoint = "search/issues"
        params = {"q": query, "per_page": per_page, "order": order}
        if sort:
            params["sort"] = sort
        return await self.github_client.make_async_request("GET", endpoint, params)
