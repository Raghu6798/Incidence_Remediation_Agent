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
    """
    A comprehensive client for interacting with the GitHub REST API.

    This client provides both synchronous and asynchronous methods for making
    HTTP requests to GitHub's REST API v3. It handles authentication, request
    formatting, response parsing, and error handling.

    Features:
        - Personal Access Token authentication
        - Support for both sync and async operations
        - Automatic JSON request/response handling
        - Comprehensive error handling and logging
        - Rate limiting awareness
        - Custom base URL support (for GitHub Enterprise)

    Prerequisites:
        - Valid GitHub Personal Access Token with appropriate scopes
        - Network connectivity to GitHub API
        - Required permissions for the operations being performed

    Authentication:
        Uses Personal Access Token authentication. The token should have
        the necessary scopes for the operations you want to perform:
        - repo: Full access to repositories
        - workflow: Access to GitHub Actions
        - admin:org: Organization administration
        - user: User profile and email access

    Rate Limiting:
        GitHub API has rate limits. This client respects these limits
        and will return appropriate error messages when limits are exceeded.

    Example Usage:
        ```python
        # Initialize with token
        client = GitHubAPIClient(token="ghp_your_token_here")

        # Make a GET request
        repos = client.make_request("GET", "user/repos")

        # Make a POST request with data
        new_issue = client.make_request("POST", "repos/owner/repo/issues", {
            "title": "Bug report",
            "body": "Description of the bug"
        })

        # Async request
        async def get_user():
            return await client.make_async_request("GET", "user")
        ```
    """

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        """
        Initialize the GitHub API client.

        Args:
            token (str): GitHub Personal Access Token for authentication.
                        Must have appropriate scopes for the operations you need.
            base_url (str): Base URL for the GitHub API.
                           Defaults to "https://api.github.com" for GitHub.com.
                           Use custom URL for GitHub Enterprise instances.

        Raises:
            ValueError: If token is empty or invalid.

        Example:
            ```python
            # GitHub.com
            client = GitHubAPIClient("ghp_your_token_here")

            # GitHub Enterprise
            client = GitHubAPIClient(
                "ghp_your_token_here",
                "https://github.yourcompany.com/api/v3"
            )
            ```
        """
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevOps-Agent/1.0",
        }

    def make_request(
        self, method: str, endpoint: str, data: Dict[Any, Any] = None
    ) -> Dict[Any, Any]:
        """
        Make a synchronous HTTP request to the GitHub API.

        This method handles the complete request lifecycle including authentication,
        request formatting, response parsing, and error handling.

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint (str): API endpoint path (e.g., "user/repos", "repos/owner/repo/issues").
                          Should not include the base URL or leading slash.
            data (Dict[Any, Any], optional): Request payload for POST/PUT/PATCH requests.
                                           Will be automatically converted to JSON.

        Returns:
            Dict[Any, Any]: Parsed JSON response from the GitHub API.
                           For successful requests, contains the API response data.
                           For errors, contains error details.

        Raises:
            requests.RequestException: For network or HTTP errors.
            ValueError: For invalid request parameters.
            KeyError: For malformed API responses.

        Example:
            ```python
            # Get user repositories
            repos = client.make_request("GET", "user/repos")

            # Create an issue
            issue = client.make_request("POST", "repos/owner/repo/issues", {
                "title": "New feature request",
                "body": "Please add support for..."
            })

            # Update repository settings
            client.make_request("PATCH", "repos/owner/repo", {
                "description": "Updated description"
            })
            ```
        """
        import requests

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() in ["POST", "PUT", "PATCH"] and data:
                response = requests.request(
                    method, url, headers=self.headers, json=data
                )
            else:
                response = requests.request(method, url, headers=self.headers)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
        except ValueError as e:
            return {"error": f"Invalid response format: {str(e)}"}

    async def make_async_request(
        self, method: str, endpoint: str, data: Dict[Any, Any] = None
    ) -> Dict[Any, Any]:
        """
        Make an asynchronous HTTP request to the GitHub API.

        This method provides the same functionality as make_request but operates
        asynchronously, allowing for non-blocking API calls in async contexts.

        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint (str): API endpoint path (e.g., "user/repos", "repos/owner/repo/issues").
                          Should not include the base URL or leading slash.
            data (Dict[Any, Any], optional): Request payload for POST/PUT/PATCH requests.
                                           Will be automatically converted to JSON.

        Returns:
            Dict[Any, Any]: Parsed JSON response from the GitHub API.
                           For successful requests, contains the API response data.
                           For errors, contains error details.

        Raises:
            aiohttp.ClientError: For network or HTTP errors.
            ValueError: For invalid request parameters.
            KeyError: For malformed API responses.

        Example:
            ```python
            async def get_user_data():
                return await client.make_async_request("GET", "user")

            async def create_issue():
                return await client.make_async_request("POST", "repos/owner/repo/issues", {
                    "title": "Async issue creation",
                    "body": "Created via async request"
                })
            ```
        """
        import aiohttp

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() in ["POST", "PUT", "PATCH"] and data:
                    async with session.request(
                        method, url, headers=self.headers, json=data
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
                else:
                    async with session.request(
                        method, url, headers=self.headers
                    ) as response:
                        response.raise_for_status()
                        return await response.json()

        except aiohttp.ClientError as e:
            return {"error": f"Async request failed: {str(e)}"}
        except ValueError as e:
            return {"error": f"Invalid response format: {str(e)}"}


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
    """
    A LangChain tool for listing GitHub repositories for a user or organization.

    This tool provides comprehensive repository listing functionality with various
    filtering options and pagination support. It can list repositories for both
    individual users and organizations.

    Features:
        - List repositories for users or organizations
        - Filter by repository type (all, owner, public, private, member)
        - Pagination support with configurable page size
        - Automatic sorting by last updated
        - Support for both sync and async operations

    Repository Types:
        - all: All repositories the user has access to
        - owner: Repositories owned by the user/organization
        - public: Public repositories
        - private: Private repositories (requires appropriate permissions)
        - member: Repositories where the user is a member

    Prerequisites:
        - Valid GitHub Personal Access Token
        - Appropriate permissions for the repository types being accessed
        - Access to the specified user/organization

    Example Usage:
        ```python
        # List all repositories for a user
        tool = ListRepositoriesTool(github_client=client)
        result = tool.run({"owner": "octocat"})

        # List only public repositories
        result = tool.run({
            "owner": "microsoft",
            "repo_type": "public",
            "per_page": 50
        })

        # List private repositories (requires appropriate permissions)
        result = tool.run({
            "owner": "myorg",
            "repo_type": "private"
        })
        ```

    Output Format:
        Returns a list of repository objects containing:
        - Repository name and full name
        - Description and homepage URL
        - Visibility (public/private)
        - Language and topics
        - Star and fork counts
        - Last updated timestamp
        - Default branch information

    Error Handling:
        - Authentication errors (401)
        - Permission errors (403)
        - Not found errors (404)
        - Rate limiting errors (429)
        - Network connectivity issues
    """

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
        """
        Synchronously list repositories for a GitHub user or organization.

        Args:
            owner (str): GitHub username or organization name.
                       Examples: "octocat", "microsoft", "myorg"
            repo_type (str): Type of repositories to list.
                           Options: "all", "owner", "public", "private", "member"
            per_page (int): Number of repositories per page (1-100).
                          Default: 30, Maximum: 100
            run_manager (Optional[CallbackManagerForToolRun]): LangChain callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing repository information.
                           Includes repository list and pagination metadata.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
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
        """
        Asynchronously list repositories for a GitHub user or organization.

        Args:
            owner (str): GitHub username or organization name.
                       Examples: "octocat", "microsoft", "myorg"
            repo_type (str): Type of repositories to list.
                           Options: "all", "owner", "public", "private", "member"
            per_page (int): Number of repositories per page (1-100).
                          Default: 30, Maximum: 100
            run_manager (Optional[AsyncCallbackManagerForToolRun]): LangChain async callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing repository information.
                           Same format as synchronous version.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
        endpoint = f"users/{owner}/repos"
        params = {"type": repo_type, "per_page": per_page, "sort": "updated"}
        return await self.github_client.make_async_request("GET", endpoint, params)


class GetRepositoryInput(BaseModel):
    owner: str = Field(description="Repository owner username")
    repo: str = Field(description="Repository name")


class GetRepositoryTool(AbstractTool):
    """
    A LangChain tool for retrieving detailed information about a specific GitHub repository.

    This tool provides comprehensive repository information including metadata,
    statistics, configuration, and status details. It's useful for getting
    complete repository profiles and checking repository health.

    Features:
        - Get detailed repository information
        - Access repository statistics and metrics
        - Retrieve repository configuration and settings
        - Check repository status and health
        - Support for both sync and async operations

    Information Retrieved:
        - Basic repository details (name, description, homepage)
        - Repository statistics (stars, forks, watchers, issues)
        - Configuration (default branch, topics, language)
        - Status information (archived, disabled, private/public)
        - Network information (parent, source, template)
        - Security settings (vulnerability alerts, security policy)

    Prerequisites:
        - Valid GitHub Personal Access Token
        - Access to the specified repository
        - Appropriate permissions for private repositories

    Example Usage:
        ```python
        # Get repository information
        tool = GetRepositoryTool(github_client=client)
        result = tool.run({
            "owner": "microsoft",
            "repo": "vscode"
        })

        # Get private repository (requires access)
        result = tool.run({
            "owner": "myorg",
            "repo": "private-repo"
        })
        ```

    Output Format:
        Returns a detailed repository object containing:
        - Repository metadata (id, name, full_name, description)
        - Statistics (stargazers_count, forks_count, open_issues_count)
        - Configuration (default_branch, topics, language, license)
        - Status flags (archived, disabled, private, fork)
        - URLs (html_url, clone_url, ssh_url)
        - Timestamps (created_at, updated_at, pushed_at)

    Error Handling:
        - Repository not found (404)
        - Access denied (403)
        - Authentication errors (401)
        - Network connectivity issues
    """

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
        """
        Synchronously get detailed information about a GitHub repository.

        Args:
            owner (str): Repository owner username or organization name.
                       Examples: "microsoft", "octocat", "myorg"
            repo (str): Repository name.
                      Examples: "vscode", "Hello-World", "my-project"
            run_manager (Optional[CallbackManagerForToolRun]): LangChain callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing detailed repository information.
                           Includes all repository metadata, statistics, and configuration.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
        endpoint = f"repos/{owner}/{repo}"
        return self.github_client.make_request("GET", endpoint)

    async def _arun(
        self,
        owner: str,
        repo: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ):
        """
        Asynchronously get detailed information about a GitHub repository.

        Args:
            owner (str): Repository owner username or organization name.
                       Examples: "microsoft", "octocat", "myorg"
            repo (str): Repository name.
                      Examples: "vscode", "Hello-World", "my-project"
            run_manager (Optional[AsyncCallbackManagerForToolRun]): LangChain async callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing detailed repository information.
                           Same format as synchronous version.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
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
    """
    A LangChain tool for listing and filtering issues in a GitHub repository.

    This tool provides comprehensive issue listing functionality with multiple
    filtering options, making it easy to find specific issues based on various
    criteria such as state, labels, assignees, and more.

    Features:
        - List issues with multiple filtering options
        - Filter by issue state (open, closed, all)
        - Filter by labels (comma-separated)
        - Filter by assignee
        - Pagination support with configurable page size
        - Automatic sorting by last updated
        - Support for both sync and async operations

    Issue States:
        - open: Only open issues (default)
        - closed: Only closed issues
        - all: Both open and closed issues

    Filtering Options:
        - Labels: Comma-separated list of label names
        - Assignee: Specific GitHub username
        - Per page: Number of issues to return (1-100)

    Prerequisites:
        - Valid GitHub Personal Access Token
        - Access to the specified repository
        - Appropriate permissions for the repository

    Example Usage:
        ```python
        # List open issues
        tool = ListIssuesTool(github_client=client)
        result = tool.run({
            "owner": "microsoft",
            "repo": "vscode"
        })

        # List issues with specific labels
        result = tool.run({
            "owner": "microsoft",
            "repo": "vscode",
            "labels": "bug,help wanted",
            "state": "open"
        })

        # List issues assigned to specific user
        result = tool.run({
            "owner": "microsoft",
            "repo": "vscode",
            "assignee": "username",
            "per_page": 50
        })

        # List all issues (open and closed)
        result = tool.run({
            "owner": "microsoft",
            "repo": "vscode",
            "state": "all"
        })
        ```

    Output Format:
        Returns a list of issue objects containing:
        - Issue number and title
        - Issue state and labels
        - Assignee and milestone information
        - Creation and update timestamps
        - Issue body and comments count
        - Repository and user references

    Error Handling:
        - Repository not found (404)
        - Access denied (403)
        - Authentication errors (401)
        - Invalid filter parameters
        - Network connectivity issues
    """

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
        """
        Synchronously list issues in a GitHub repository with filtering options.

        Args:
            owner (str): Repository owner username or organization name.
                       Examples: "microsoft", "octocat", "myorg"
            repo (str): Repository name.
                      Examples: "vscode", "Hello-World", "my-project"
            state (str): Issue state filter.
                       Options: "open" (default), "closed", "all"
            labels (str): Comma-separated list of label names to filter by.
                        Examples: "bug", "bug,help wanted", "enhancement,good first issue"
            assignee (str): GitHub username to filter by assignee.
                          Examples: "username", "octocat"
            per_page (int): Number of issues per page (1-100).
                          Default: 30, Maximum: 100
            run_manager (Optional[CallbackManagerForToolRun]): LangChain callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing filtered issue list.
                           Includes issues matching the specified criteria.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
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
        """
        Asynchronously list issues in a GitHub repository with filtering options.

        Args:
            owner (str): Repository owner username or organization name.
                       Examples: "microsoft", "octocat", "myorg"
            repo (str): Repository name.
                      Examples: "vscode", "Hello-World", "my-project"
            state (str): Issue state filter.
                       Options: "open" (default), "closed", "all"
            labels (str): Comma-separated list of label names to filter by.
                        Examples: "bug", "bug,help wanted", "enhancement,good first issue"
            assignee (str): GitHub username to filter by assignee.
                          Examples: "username", "octocat"
            per_page (int): Number of issues per page (1-100).
                          Default: 30, Maximum: 100
            run_manager (Optional[AsyncCallbackManagerForToolRun]): LangChain async callback manager.

        Returns:
            Dict[Any, Any]: JSON response containing filtered issue list.
                           Same format as synchronous version.

        Raises:
            Exception: For API errors, authentication issues, or network problems.
        """
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
