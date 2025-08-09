"""
Enhanced and Base Jenkins Client Tools for DevOps Incident Response Agent.
This script combines base Jenkins operations (trigger, status, info, console) with
enhanced capabilities (monitor, health check, emergency deploy, rollback)
for comprehensive CI/CD integration during incidents.
"""
import os
import json
import time
import requests
import asyncio
import aiohttp
from typing import Optional, Type, Dict, Any, List
from urllib.parse import urljoin

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from tools.base import AbstractTool, ToolInputSchema

load_dotenv()

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
        kwargs.setdefault('timeout', 30)
        response = requests.request(method, url, auth=self.auth, **kwargs)
        response.raise_for_status()
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        return {"content": response.text}

    async def _async_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Async version of _request using aiohttp"""
        url = self._make_url(endpoint)
        timeout = aiohttp.ClientTimeout(total=kwargs.pop('timeout', 30))
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            auth = aiohttp.BasicAuth(self.auth[0], self.auth[1])
            async with session.request(method, url, auth=auth, **kwargs) as response:
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return await response.json()
                text = await response.text()
                return {"content": text}

    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        return self._request('GET', f"/job/{job_name}/api/json")

    async def async_get_job_info(self, job_name: str) -> Dict[str, Any]:
        return await self._async_request('GET', f"/job/{job_name}/api/json")

    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        return self._request('GET', f"/job/{job_name}/{build_number}/api/json")

    async def async_get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        return await self._async_request('GET', f"/job/{job_name}/{build_number}/api/json")

    def get_last_build_info(self, job_name: str) -> Dict[str, Any]:
        return self._request('GET', f"/job/{job_name}/lastBuild/api/json")

    async def async_get_last_build_info(self, job_name: str) -> Dict[str, Any]:
        return await self._async_request('GET', f"/job/{job_name}/lastBuild/api/json")

    def get_console_output(self, job_name: str, build_number: int) -> str:
        response = self._request('GET', f"/job/{job_name}/{build_number}/consoleText")
        return response.get("content", "Could not retrieve console output.")

    async def async_get_console_output(self, job_name: str, build_number: int) -> str:
        response = await self._async_request('GET', f"/job/{job_name}/{build_number}/consoleText")
        return response.get("content", "Could not retrieve console output.")

    def trigger_build(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        endpoint = f"/job/{job_name}/build"
        if parameters:
            endpoint += "WithParameters"
            return self._request('POST', endpoint, params=parameters)
        return self._request('POST', endpoint)

    async def async_trigger_build(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        endpoint = f"/job/{job_name}/build"
        if parameters:
            endpoint += "WithParameters"
            return await self._async_request('POST', endpoint, params=parameters)
        return await self._async_request('POST', endpoint)
    
    def wait_for_build_completion(self, job_name: str, build_number: int, timeout: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                build_info = self.get_build_info(job_name, build_number)
                if not build_info.get("building", True):
                    return {"status": "COMPLETED", "result": build_info.get("result"), "info": build_info}
                time.sleep(10)
            except Exception as e:
                return {"status": "ERROR", "error": f"Failed to get build info during wait: {e}"}
        return {"status": "TIMEOUT", "error": "Timeout waiting for build completion"}

    async def async_wait_for_build_completion(self, job_name: str, build_number: int, timeout: int = 300) -> Dict[str, Any]:
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                build_info = await self.async_get_build_info(job_name, build_number)
                if not build_info.get("building", True):
                    return {"status": "COMPLETED", "result": build_info.get("result"), "info": build_info}
                await asyncio.sleep(10)
            except Exception as e:
                return {"status": "ERROR", "error": f"Failed to get build info during wait: {e}"}
        return {"status": "TIMEOUT", "error": "Timeout waiting for build completion"}

    def get_pipeline_health(self, pipeline_names: List[str]) -> Dict[str, Any]:
        health_report = {"overall_status": "HEALTHY", "pipelines": {}}
        issues = []
        for name in pipeline_names:
            try:
                last_build = self.get_last_build_info(name)
                status = last_build.get("result", "UNKNOWN")
                health_report["pipelines"][name] = {"status": status, "last_build_number": last_build.get("number")}
                if status not in ["SUCCESS", "UNSTABLE"]:
                    issues.append(name)
            except Exception:
                health_report["pipelines"][name] = {"status": "NOT_FOUND", "error": "Could not retrieve job info."}
                issues.append(name)
        if issues:
            health_report["overall_status"] = "UNHEALTHY"
        return health_report

    async def async_get_pipeline_health(self, pipeline_names: List[str]) -> Dict[str, Any]:
        health_report = {"overall_status": "HEALTHY", "pipelines": {}}
        issues = []
        
        # Use asyncio.gather to fetch all pipeline info concurrently
        async def get_pipeline_info(name: str):
            try:
                last_build = await self.async_get_last_build_info(name)
                status = last_build.get("result", "UNKNOWN")
                return name, {"status": status, "last_build_number": last_build.get("number")}, status not in ["SUCCESS", "UNSTABLE"]
            except Exception:
                return name, {"status": "NOT_FOUND", "error": "Could not retrieve job info."}, True

        results = await asyncio.gather(*[get_pipeline_info(name) for name in pipeline_names], return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                continue
            name, info, has_issue = result
            health_report["pipelines"][name] = info
            if has_issue:
                issues.append(name)
                
        if issues:
            health_report["overall_status"] = "UNHEALTHY"
        return health_report

# --- Input Schemas ---
class TriggerBuildInput(ToolInputSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline to trigger.")
    parameters: Optional[Dict[str, str]] = Field(default=None, description="Build parameters as key-value pairs.")

class JobStatusInput(ToolInputSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline to check the status of its last build.")

class BuildInfoInput(ToolInputSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline.")
    build_number: int = Field(description="The specific build number to get information for.")

class ConsoleOutputInput(ToolInputSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline.")
    build_number: int = Field(description="The build number to get the console output for.")
    tail_lines: Optional[int] = Field(default=100, description="Number of lines from the end of the log to return.")

class PipelineMonitorInput(ToolInputSchema):
    job_name: str = Field(description="Name of the Jenkins job/pipeline.")
    build_number: int = Field(description="The build number to monitor.")
    timeout: int = Field(default=600, description="Timeout in seconds to wait for the build to complete.")

class RollbackInput(ToolInputSchema):
    job_name: str = Field(description="Name of the rollback job/pipeline.")
    environment: str = Field(description="The target environment for the rollback (e.g., 'production', 'staging').")
    version_to_restore: str = Field(description="The specific application version to restore.")

class EmergencyDeployInput(ToolInputSchema):
    job_name: str = Field(description="Name of the emergency deployment job.")
    branch_or_commit: str = Field(description="The Git branch or commit hash for the emergency deploy.")
    environment: str = Field(description="The target environment for deployment (e.g., 'production', 'staging').")

class HealthCheckInput(ToolInputSchema):
    pipeline_names: List[str] = Field(description="A list of critical pipeline names to include in the health check.")

# --- Tool Definitions ---

class JenkinsTriggerBuildTool(AbstractTool):
    name: str = "jenkins_trigger_build"
    description: str = "Triggers a Jenkins build for a specified job, optionally with parameters."
    args_schema: Type[ToolInputSchema] = TriggerBuildInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> str:
        try:
            result = self.jenkins_client.trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Build triggered successfully.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, parameters: Optional[Dict[str, str]] = None) -> str:
        try:
            result = await self.jenkins_client.async_trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Build triggered successfully.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsJobStatusTool(AbstractTool):
    name: str = "jenkins_job_status"
    description: str = "Gets the status of the last build for a specified Jenkins job."
    args_schema: Type[ToolInputSchema] = JobStatusInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str) -> str:
        try:
            info = self.jenkins_client.get_last_build_info(job_name)
            return json.dumps({
                "success": True,
                "status": {
                    "job_name": job_name,
                    "build_number": info.get("number"),
                    "is_building": info.get("building"),
                    "result": info.get("result", "IN_PROGRESS"),
                }
            })
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str) -> str:
        try:
            info = await self.jenkins_client.async_get_last_build_info(job_name)
            return json.dumps({
                "success": True,
                "status": {
                    "job_name": job_name,
                    "build_number": info.get("number"),
                    "is_building": info.get("building"),
                    "result": info.get("result", "IN_PROGRESS"),
                }
            })
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsBuildInfoTool(AbstractTool):
    name: str = "jenkins_build_info"
    description: str = "Gets detailed information for a specific build number of a Jenkins job."
    args_schema: Type[ToolInputSchema] = BuildInfoInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, build_number: int) -> str:
        try:
            info = self.jenkins_client.get_build_info(job_name, build_number)
            return json.dumps({"success": True, "build_info": info})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, build_number: int) -> str:
        try:
            info = await self.jenkins_client.async_get_build_info(job_name, build_number)
            return json.dumps({"success": True, "build_info": info})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsConsoleOutputTool(AbstractTool):
    name: str = "jenkins_console_output"
    description: str = "Retrieves the console log for a specific Jenkins build. Can tail the log."
    args_schema: Type[ToolInputSchema] = ConsoleOutputInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, build_number: int, tail_lines: int = 100) -> str:
        try:
            output = self.jenkins_client.get_console_output(job_name, build_number)
            log_lines = output.splitlines()
            tailed_output = "\n".join(log_lines[-tail_lines:])
            return json.dumps({"success": True, "log_output": tailed_output})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, build_number: int, tail_lines: int = 100) -> str:
        try:
            output = await self.jenkins_client.async_get_console_output(job_name, build_number)
            log_lines = output.splitlines()
            tailed_output = "\n".join(log_lines[-tail_lines:])
            return json.dumps({"success": True, "log_output": tailed_output})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsGetLastBuildInfoTool(AbstractTool):
    name: str = "jenkins_get_last_build_info"
    description: str = "Retrieves detailed information about the most recent build of a Jenkins job."
    args_schema: Type[ToolInputSchema] = JobStatusInput # Re-using JobStatusInput is fine here
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str) -> str:
        try:
            info = self.jenkins_client.get_last_build_info(job_name)
            return json.dumps({"success": True, "last_build_info": info})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str) -> str:
        try:
            info = await self.jenkins_client.async_get_last_build_info(job_name)
            return json.dumps({"success": True, "last_build_info": info})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsPipelineMonitorTool(AbstractTool):
    name: str = "jenkins_pipeline_monitor"
    description: str = "Monitors a specific Jenkins build until it completes or times out."
    args_schema: Type[ToolInputSchema] = PipelineMonitorInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, build_number: int, timeout: int = 600) -> str:
        try:
            result = self.jenkins_client.wait_for_build_completion(job_name, build_number, timeout)
            return json.dumps({"success": True, "monitoring_result": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, build_number: int, timeout: int = 600) -> str:
        try:
            result = await self.jenkins_client.async_wait_for_build_completion(job_name, build_number, timeout)
            return json.dumps({"success": True, "monitoring_result": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsHealthCheckTool(AbstractTool):
    name: str = "jenkins_health_check"
    description: str = "Performs a health check on a list of critical Jenkins pipelines by checking their last build status."
    args_schema: Type[ToolInputSchema] = HealthCheckInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, pipeline_names: List[str]) -> str:
        try:
            report = self.jenkins_client.get_pipeline_health(pipeline_names)
            return json.dumps({"success": True, "health_report": report})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, pipeline_names: List[str]) -> str:
        try:
            report = await self.jenkins_client.async_get_pipeline_health(pipeline_names)
            return json.dumps({"success": True, "health_report": report})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsEmergencyDeployTool(AbstractTool):
    name: str = "jenkins_emergency_deploy"
    description: str = "Triggers an emergency deployment pipeline with a specific branch or commit."
    args_schema: Type[ToolInputSchema] = EmergencyDeployInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, environment: str, branch_or_commit: str) -> str:
        parameters = {"ENVIRONMENT": environment, "GIT_REF": branch_or_commit}
        try:
            result = self.jenkins_client.trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Emergency deploy triggered.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, environment: str, branch_or_commit: str) -> str:
        parameters = {"ENVIRONMENT": environment, "GIT_REF": branch_or_commit}
        try:
            result = await self.jenkins_client.async_trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Emergency deploy triggered.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

class JenkinsRollbackTool(AbstractTool):
    name: str = "jenkins_rollback"
    description: str = "Triggers a rollback pipeline to restore a previous version in an environment."
    args_schema: Type[ToolInputSchema] = RollbackInput
    jenkins_client: EnhancedJenkinsClient
    
    def _run(self, job_name: str, environment: str, version_to_restore: str) -> str:
        parameters = {"ENVIRONMENT": environment, "VERSION_TO_RESTORE": version_to_restore}
        try:
            result = self.jenkins_client.trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Rollback triggered.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

    async def _arun(self, job_name: str, environment: str, version_to_restore: str) -> str:
        parameters = {"ENVIRONMENT": environment, "VERSION_TO_RESTORE": version_to_restore}
        try:
            result = await self.jenkins_client.async_trigger_build(job_name, parameters)
            return json.dumps({"success": True, "message": "Rollback triggered.", "details": result})
        except Exception as e: 
            return json.dumps({"success": False, "error": str(e)})

# --- Tool Factory (Now complete) ---
class JenkinsToolFactory:
    """Factory for creating all Jenkins tools with a shared client."""
    def __init__(self, base_url: str, username: str, api_token: str):
        self.jenkins_client = EnhancedJenkinsClient(base_url, username, api_token)

    def create_all_tools(self) -> List[AbstractTool]:
        """Create all Jenkins tools, both base and enhanced."""
        all_tool_classes = [
            JenkinsTriggerBuildTool,
            JenkinsJobStatusTool,
            JenkinsBuildInfoTool,
            JenkinsConsoleOutputTool,
            JenkinsGetLastBuildInfoTool,
            JenkinsPipelineMonitorTool,
            JenkinsHealthCheckTool,
            JenkinsEmergencyDeployTool,
            JenkinsRollbackTool,
        ]
        return [tool_class(jenkins_client=self.jenkins_client) for tool_class in all_tool_classes]

# --- Example Usage ---
if __name__ == "__main__":
    async def test_async_functionality():
        try:
            JENKINS_URL = os.getenv("JENKINS_URL")
            JENKINS_USERNAME = os.getenv("JENKINS_USERNAME")
            JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")

            print("Initializing JenkinsToolFactory...")
            factory = JenkinsToolFactory(
                base_url=JENKINS_URL,
                username=JENKINS_USERNAME,
                api_token=JENKINS_API_TOKEN
            )
            all_jenkins_tools = factory.create_all_tools()

            print(f"\nSuccessfully created {len(all_jenkins_tools)} Jenkins tools:")
            for tool in all_jenkins_tools:
                print(f"- {tool.name}: {tool.description}")

            print("\n--- Example: Demonstrating both sync and async methods ---")
            status_tool = next((t for t in all_jenkins_tools if t.name == 'jenkins_job_status'), None)
            if status_tool:
                job_name_to_check = "production-deployment-pipeline"
                
                print(f"\n1. Testing sync method for job '{job_name_to_check}'...")
                sync_result = status_tool._run(job_name=job_name_to_check)
                print("Sync Result:", json.loads(sync_result))
                
                print(f"\n2. Testing async method for job '{job_name_to_check}'...")
                async_result = await status_tool._arun(job_name=job_name_to_check)
                print("Async Result:", json.loads(async_result))
            else:
                print("Could not find the 'jenkins_job_status' tool to demonstrate.")

        except ValueError as e:
            print(f"\nERROR: Initialization failed. {e}")
            print("Please set JENKINS_URL, JENKINS_USERNAME, and JENKINS_API_TOKEN environment variables in a .env file.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

    # Run the async test
    try:
        asyncio.run(test_async_functionality())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    except Exception as e:
        print(f"\nFailed to run async test: {e}")