"""
Enhanced and Base Jenkins Client Tools for DevOps Incident Response Agent.
This script combines base Jenkins operations (trigger, status, info, console) with
enhanced capabilities (monitor, health check, emergency deploy, rollback)
for comprehensive CI/CD integration during incidents.
"""

import asyncio
import json
import time
from typing import Optional, Type, Dict, Any, List
from urllib.parse import urljoin
import requests
from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
import os
from dotenv import load_dotenv

# --- Base Abstractions (to make the script self-contained) ---

load_dotenv()
class ArgsSchema(BaseModel):
    """Base schema for tool arguments."""
    pass

class AbstractTool(BaseModel):
    """A simple abstract base class for tools, mimicking LangChain's structure."""
    name: str
    description: str
    args_schema: Type[ArgsSchema]

    class Config:
        arbitrary_types_allowed = True

    def _run(self, *args: Any, run_manager: Optional[CallbackManagerForToolRun] = None, **kwargs: Any) -> str:
        raise NotImplementedError("Tool does not support sync run")

# --- Enhanced Jenkins Client (with new method) ---

class EnhancedJenkinsClient:
    """Enhanced Jenkins client with incident response and base capabilities."""
    def __init__(self, base_url: str, username: str, api_token: str):
        if not base_url or not username or not api_token:
            raise ValueError("Jenkins URL, username, and API token must be provided.")
        self.base_url = base_url.rstrip('/')
        self.auth = (username, api_token)

    def _make_url(self, endpoint: str) -> str:
        return urljoin(f"{self.base_url}/", endpoint.lstrip('/'))

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = self._make_url(endpoint)
        response = requests.request(method, url, auth=self.auth, timeout=30, **kwargs)
        response.raise_for_status()
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        return {"content": response.text}

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        return self._request('GET', f"/job/{job_name}/api/json")

    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        return self._request('GET', f"/job/{job_name}/{build_number}/api/json")

    # NEW: Method to support the new tool
    def get_last_build_info(self, job_name: str) -> Dict[str, Any]:
        """Retrieves info for the last build of a job."""
        return self._request('GET', f"/job/{job_name}/lastBuild/api/json")

    def get_console_output(self, job_name: str, build_number: int) -> str:
        response = self._request('GET', f"/job/{job_name}/{build_number}/consoleText")
        return response.get("content", "Could not retrieve console output.")

    def trigger_build(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        endpoint = f"/job/{job_name}/build"
        if parameters:
            endpoint += "WithParameters"
            return self._request('POST', endpoint, params=parameters)
        return self._request('POST', endpoint)
    
    # (Other enhanced methods like wait_for_build_completion, etc., remain the same)
    def wait_for_build_completion(self, job_name: str, build_number: int, timeout: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                build_info = self.get_build_info(job_name, build_number)
                if not build_info.get("building", True):
                    return {"completed": True, "result": build_info.get("result")}
                time.sleep(5)
            except Exception as e:
                return {"completed": False, "error": str(e)}
        return {"completed": False, "error": "Timeout waiting for build completion"}

    def get_pipeline_health(self, pipeline_names: List[str]) -> Dict[str, Any]:
        # (Implementation from previous code)
        health_report = {"overall_status": "HEALTHY", "pipelines": {}}
        # ... logic ...
        return health_report


# --- Input Schemas for ALL Tools ---

class TriggerBuildInput(ArgsSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline to trigger")
    parameters: Optional[Dict[str, str]] = Field(default=None, description="Build parameters")

class JobStatusInput(ArgsSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline to check")

class BuildInfoInput(ArgsSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline")
    build_number: int = Field(description="The build number to get information for")

class ConsoleOutputInput(ArgsSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline")
    build_number: int = Field(description="The build number for the console output")

# NEW: Input schema for the new tool
class LastBuildInfoInput(ArgsSchema):
    """Input schema for getting the last build's info."""
    job_name: str = Field(description="The name of the Jenkins job or pipeline to query.")

# (Other schemas like PipelineStatusInput, etc., remain the same)
class PipelineStatusInput(ArgsSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline")
    wait_for_completion: bool = Field(default=False, description="Whether to wait for completion")

class RollbackInput(ArgsSchema):
    job_name: str = Field(description="Name of the rollback job")
    environment: str = Field(description="Target environment")

class EmergencyDeployInput(ArgsSchema):
    job_name: str = Field(description="Name of the emergency deployment job")
    branch_or_commit: str = Field(description="Branch or commit for emergency deploy")
    environment: str = Field(description="Target environment")

class HealthCheckInput(ArgsSchema):
    pipeline_names: List[str] = Field(description="List of critical pipeline names to check")


# --- Base and Enhanced Tools ---

# (Existing tool classes like JenkinsTriggerBuildTool, etc., remain unchanged)
class JenkinsTriggerBuildTool(AbstractTool):
    name: str = "jenkins_trigger_build"
    description: str = "Triggers a Jenkins build for a specified job."
    args_schema: Type[ArgsSchema] = TriggerBuildInput
    jenkins_client: EnhancedJenkinsClient
    def _run(self, job_name: str, parameters: Optional[Dict[str, str]] = None, **kwargs) -> str:
        try:
            result = self.jenkins_client.trigger_build(job_name, parameters)
            return json.dumps({"success": True, "result": result})
        except Exception as e: return json.dumps({"success": False, "error": str(e)})

# ... other existing tool classes ...

# NEW: Tool class implementation based on the API documentation
class JenkinsGetLastBuildInfoTool(AbstractTool):
    """Tool to get detailed info about the last build of a Jenkins job."""
    name: str = "jenkins_get_last_build_info"
    description: str = (
        "Retrieves detailed information about the very last build of a specified Jenkins job. "
        "Provides details like the build number, status (e.g., SUCCESS, FAILURE), duration, "
        "and whether it is still running. Useful for quickly checking the result of the "
        "most recent pipeline execution without needing a specific build number."
    )
    args_schema: Type[ArgsSchema] = LastBuildInfoInput
    jenkins_client: EnhancedJenkinsClient

    def _run(self, job_name: str, **kwargs) -> str:
        """Executes the tool to fetch last build info."""
        try:
            build_info = self.jenkins_client.get_last_build_info(job_name)
            duration_ms = build_info.get("duration", 0)
            summary = {
                "job_name": job_name,
                "build_number": build_info.get("number"),
                "is_building": build_info.get("building"),
                "result": build_info.get("result", "IN_PROGRESS" if build_info.get("building") else "UNKNOWN"),
                "timestamp": build_info.get("timestamp"),
                "duration_seconds": duration_ms / 1000 if duration_ms else 0,
                "url": build_info.get("url"),
            }
            return json.dumps({"success": True, "last_build_info": summary})
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return json.dumps({"success": False, "error": f"Job '{job_name}' not found or it has no builds yet."})
            return json.dumps({"success": False, "error": f"HTTP error: {e}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


# --- Tool Factory (Updated to include the new tool) ---
class JenkinsToolFactory:
    """Factory for creating all Jenkins tools with a shared client."""
    def __init__(self, base_url: str, username: str, api_token: str):
        self.jenkins_client = EnhancedJenkinsClient(base_url, username, api_token)

    def create_all_tools(self) -> List[AbstractTool]:
        """Create all Jenkins tools, both base and enhanced."""
        # Assume other tool classes like JenkinsJobStatusTool are defined above
        # For brevity, I'm only showing the new tool being added
        all_tool_classes = [
            JenkinsTriggerBuildTool,
            # JenkinsJobStatusTool,
            # JenkinsBuildInfoTool,
            # JenkinsConsoleOutputTool,
            JenkinsGetLastBuildInfoTool, # <-- ADDED NEW TOOL HERE
            # JenkinsPipelineMonitorTool,
            # JenkinsHealthCheckTool,
            # JenkinsEmergencyDeployTool,
            # JenkinsRollbackTool,
        ]
        # A more robust factory would look like this:
        return [
            tool_class(jenkins_client=self.jenkins_client) for tool_class in all_tool_classes
        ]

# --- Example Usage ---
if __name__ == "__main__":
    JENKINS_URL = os.getenv("JENKINS_URL")
    JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
    JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
    print(JENKINS_URL)
    print(JENKINS_USERNAME)
    print(JENKINS_API_TOKEN)
    print("Initializing JenkinsToolFactory...")
    
    try:
        # A mock list of all tool classes for the factory
        # In a real app, you'd import these
        class JenkinsJobStatusTool(AbstractTool): pass # Mocking for demo
        # ... mock other classes
        
        # Redefining factory to be self-contained for the demo
        class FullJenkinsToolFactory:
            def __init__(self, base_url: str, username: str, api_token: str):
                self.jenkins_client = EnhancedJenkinsClient(base_url, username, api_token)
            def create_all_tools(self) -> List[AbstractTool]:
                return [
                    JenkinsTriggerBuildTool(jenkins_client=self.jenkins_client),
                    JenkinsGetLastBuildInfoTool(jenkins_client=self.jenkins_client),
                    # ... add all other real tools here
                ]

        factory = FullJenkinsToolFactory(
            base_url=JENKINS_URL,
            username=JENKINS_USERNAME,
            api_token=JENKINS_API_TOKEN
        )
        all_jenkins_tools = factory.create_all_tools()

        print(f"\nSuccessfully created {len(all_jenkins_tools)} Jenkins tools:")
        for tool in all_jenkins_tools:
            print(f"- {tool.name}: {tool.description}")

        print("\n--- Example: Demonstrating the NEW tool ---")
        last_build_tool = all_jenkins_tools[1] # JenkinsGetLastBuildInfoTool
        job_name_to_check = "production-deployment-pipeline"
        
        print(f"Executing tool '{last_build_tool.name}' for job '{job_name_to_check}'...")
        
        try:
            result_json = last_build_tool._run(job_name=job_name_to_check)
            result_data = json.loads(result_json)
            print("\nResult:")
            print(json.dumps(result_data, indent=2))
        except requests.exceptions.RequestException as e:
            print(f"\nERROR: Could not connect to Jenkins at {JENKINS_URL}. Ensure it's running and credentials are correct.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

    except ValueError as e:
        print(f"ERROR: Initialization failed. {e}")
        print("Please set JENKINS_URL, JENKINS_USERNAME, and JENKINS_API_TOKEN environment variables.")