import asyncio
import json
import time
from typing import Optional, Type, Dict, Any, List
from ..base import AbstractTool, ArgsSchema
from urllib.parse import urljoin
import aiohttp
import requests
from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

class JenkinsClient:
    """Jenkins API client for incident response operations."""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.auth = (username, api_token)
        
    def _make_url(self, endpoint: str) -> str:
        """Construct full URL for Jenkins API endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
    
    def get_job_info(self, job_name: str) -> Dict[str, Any]:
        """Get information about a specific Jenkins job."""
        url = self._make_url(f"job/{job_name}/api/json")
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()
    
    def trigger_build(self, job_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Trigger a Jenkins job build."""
        if parameters:
            url = self._make_url(f"job/{job_name}/buildWithParameters")
            response = requests.post(url, auth=self.auth, data=parameters)
        else:
            url = self._make_url(f"job/{job_name}/build")
            response = requests.post(url, auth=self.auth)
        
        response.raise_for_status()
        
        # Get queue item location from response headers
        queue_url = response.headers.get('Location')
        if queue_url:
            return {"status": "triggered", "queue_url": queue_url}
        return {"status": "triggered"}
    
    def get_build_info(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Get information about a specific build."""
        url = self._make_url(f"job/{job_name}/{build_number}/api/json")
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()
    
    def get_last_build_info(self, job_name: str) -> Dict[str, Any]:
        """Get information about the last build of a job."""
        url = self._make_url(f"job/{job_name}/lastBuild/api/json")
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()
    
    def stop_build(self, job_name: str, build_number: int) -> Dict[str, Any]:
        """Stop a running build."""
        url = self._make_url(f"job/{job_name}/{build_number}/stop")
        response = requests.post(url, auth=self.auth)
        response.raise_for_status()
        return {"status": "stopped", "job": job_name, "build": build_number}
    
    def get_console_output(self, job_name: str, build_number: int) -> str:
        """Get console output for a specific build."""
        url = self._make_url(f"job/{job_name}/{build_number}/consoleText")
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.text
    
    async def async_get_job_info(self, job_name: str) -> Dict[str, Any]:
        """Async version of get_job_info."""
        url = self._make_url(f"job/{job_name}/api/json")
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.api_token)
        ) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
    
    async def async_trigger_build(self, job_name: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Async version of trigger_build."""
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.api_token)
        ) as session:
            if parameters:
                url = self._make_url(f"job/{job_name}/buildWithParameters")
                async with session.post(url, data=parameters) as response:
                    response.raise_for_status()
                    queue_url = response.headers.get('Location')
            else:
                url = self._make_url(f"job/{job_name}/build")
                async with session.post(url) as response:
                    response.raise_for_status()
                    queue_url = response.headers.get('Location')
            
            if queue_url:
                return {"status": "triggered", "queue_url": queue_url}
            return {"status": "triggered"}

class TriggerBuildInput(BaseModel):
    """Input schema for triggering Jenkins builds."""
    job_name: str = Field(description="Name of the Jenkins job to trigger")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Build parameters as key-value pairs"
    )

class JobInfoInput(BaseModel):
    """Input schema for getting job information."""
    job_name: str = Field(description="Name of the Jenkins job")


class BuildInfoInput(BaseModel):
    """Input schema for getting build information."""
    job_name: str = Field(description="Name of the Jenkins job")
    build_number: Optional[int] = Field(
        default=None, 
        description="Build number (if not provided, gets last build)"
    )


class StopBuildInput(BaseModel):
    """Input schema for stopping a build."""
    job_name: str = Field(description="Name of the Jenkins job")
    build_number: int = Field(description="Build number to stop")


class ConsoleOutputInput(BaseModel):
    """Input schema for getting console output."""
    job_name: str = Field(description="Name of the Jenkins job")
    build_number: int = Field(description="Build number")




class JenkinsTriggerBuildTool(AbstractTool):
    """Tool for triggering Jenkins builds during incident response."""
    
    name: str = "jenkins_trigger_build"
    description: str = (
        "Trigger a Jenkins job build. Useful for deploying hotfixes, "
        "running diagnostic scripts, or executing incident response playbooks. "
        "Can pass parameters to parameterized builds."
    )
    args_schema: Type[BaseModel] = TriggerBuildInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self, 
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Trigger a Jenkins build synchronously."""
        try:
            result = self.jenkins_client.trigger_build(job_name, parameters)
            return json.dumps({
                "success": True,
                "job_name": job_name,
                "parameters": parameters,
                "result": result
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name
            })
    
    async def _arun(
        self,
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        """Trigger a Jenkins build asynchronously."""
        try:
            result = await self.jenkins_client.async_trigger_build(job_name, parameters)
            return json.dumps({
                "success": True,
                "job_name": job_name,
                "parameters": parameters,
                "result": result
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name
            })


class JenkinsJobStatusTool(AbstractTool):
    """Tool for checking Jenkins job status during incident response."""
    
    name: str = "jenkins_job_status"
    description: str = (
        "Get status and information about a Jenkins job. "
        "Useful for checking if incident response jobs are healthy, "
        "getting last build status, or monitoring deployment pipelines."
    )
    args_schema: Type[BaseModel] = JobInfoInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self, 
        job_name: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Get job status synchronously."""
        try:
            job_info = self.jenkins_client.get_job_info(job_name)
            
            # Extract key information for incident response
            status_info = {
                "job_name": job_name,
                "buildable": job_info.get("buildable", False),
                "last_build": job_info.get("lastBuild", {}),
                "last_successful_build": job_info.get("lastSuccessfulBuild", {}),
                "last_failed_build": job_info.get("lastFailedBuild", {}),
                "health_report": job_info.get("healthReport", [])
            }
            
            return json.dumps({
                "success": True,
                "status": status_info
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name
            })
    
    async def _arun(
        self,
        job_name: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        """Get job status asynchronously."""
        try:
            job_info = await self.jenkins_client.async_get_job_info(job_name)
            
            status_info = {
                "job_name": job_name,
                "buildable": job_info.get("buildable", False),
                "last_build": job_info.get("lastBuild", {}),
                "last_successful_build": job_info.get("lastSuccessfulBuild", {}),
                "last_failed_build": job_info.get("lastFailedBuild", {}),
                "health_report": job_info.get("healthReport", [])
            }
            
            return json.dumps({
                "success": True,
                "status": status_info
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name
            })


class JenkinsBuildInfoTool(AbstractTool):
    """Tool for getting detailed build information."""
    
    name: str = "jenkins_build_info"
    description: str = (
        "Get detailed information about a specific Jenkins build or the last build. "
        "Useful for checking build results, getting timestamps, and understanding "
        "what happened during incident response build executions."
    )
    args_schema: Type[BaseModel] = BuildInfoInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self, 
        job_name: str,
        build_number: Optional[int] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Get build information synchronously."""
        try:
            if build_number:
                build_info = self.jenkins_client.get_build_info(job_name, build_number)
            else:
                build_info = self.jenkins_client.get_last_build_info(job_name)
            
            # Extract key information
            result_info = {
                "job_name": job_name,
                "build_number": build_info.get("number"),
                "result": build_info.get("result"),
                "building": build_info.get("building", False),
                "duration": build_info.get("duration"),
                "timestamp": build_info.get("timestamp"),
                "url": build_info.get("url"),
                "actions": build_info.get("actions", [])
            }
            
            return json.dumps({
                "success": True,
                "build_info": result_info
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name,
                "build_number": build_number
            })
    
    async def _arun(
        self,
        job_name: str,
        build_number: Optional[int] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        """Get build information asynchronously."""
        # For async, we'll use the sync version wrapped in asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._run, job_name, build_number, run_manager, **kwargs
        )


class JenkinsConsoleOutputTool(AbstractTool):
    """Tool for getting Jenkins build console output."""
    
    name: str = "jenkins_console_output"
    description: str = (
        "Get console output from a Jenkins build. "
        "Useful for debugging failed builds, checking logs during incident response, "
        "or getting detailed information about what happened during execution."
    )
    args_schema: Type[BaseModel] = ConsoleOutputInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self, 
        job_name: str,
        build_number: int,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """Get console output synchronously."""
        try:
            console_output = self.jenkins_client.get_console_output(job_name, build_number)
            
            # Truncate if too long (keep last 5000 chars for most relevant info)
            if len(console_output) > 5000:
                console_output = "...\n" + console_output[-5000:]
            
            return json.dumps({
                "success": True,
                "job_name": job_name,
                "build_number": build_number,
                "console_output": console_output
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "job_name": job_name,
                "build_number": build_number
            })
    
    async def _arun(
        self,
        job_name: str,
        build_number: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        """Get console output asynchronously."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._run, job_name, build_number, run_manager, **kwargs
        )
    

class PipelineStatusInput(BaseModel):
    """Input schema for monitoring pipeline status."""
    job_name: str = Field(description="Name of the Jenkins job/pipeline")
    wait_for_completion: bool = Field(
        default=False, 
        description="Whether to wait for the build to complete"
    )
    timeout_seconds: int = Field(
        default=300, 
        description="Timeout for waiting (default 5 minutes)"
    )

class RollbackInput(BaseModel):
    """Input schema for rollback operations."""
    job_name: str = Field(description="Name of the rollback job")
    target_version: Optional[str] = Field(
        default=None, 
        description="Target version/commit to rollback to"
    )
    environment: str = Field(description="Target environment (staging, production, etc.)")

class EmergencyDeployInput(BaseModel):
    """Input schema for emergency deployments."""
    job_name: str = Field(description="Name of the emergency deployment job")
    branch_or_commit: str = Field(description="Branch or commit hash for emergency deploy")
    environment: str = Field(description="Target environment")
    skip_tests: bool = Field(default=False, description="Skip tests for faster deployment")
    reason: str = Field(description="Reason for emergency deployment")

class HealthCheckInput(BaseModel):
    """Input schema for CI/CD health checks."""
    pipeline_names: List[str] = Field(description="List of critical pipeline names to check")

# Enhanced Jenkins Client
class JenkinsClient:
    """Enhanced Jenkins client with incident response specific capabilities."""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.auth = (username, api_token)
    
    def _make_url(self, endpoint: str) -> str:
        """Construct full URL for Jenkins API endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
    
    def wait_for_build_completion(self, job_name: str, build_number: int, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a build to complete with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                build_info = self.get_build_info(job_name, build_number)
                if not build_info.get("building", True):
                    return {
                        "completed": True,
                        "result": build_info.get("result"),
                        "duration": build_info.get("duration"),
                        "build_info": build_info
                    }
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                return {"completed": False, "error": str(e)}
        
        return {"completed": False, "error": "Timeout waiting for build completion"}
    
    def get_pipeline_health(self, pipeline_names: List[str]) -> Dict[str, Any]:
        """Check health of multiple pipelines."""
        health_report = {
            "timestamp": time.time(),
            "overall_status": "HEALTHY",
            "pipelines": {}
        }
        
        unhealthy_count = 0
        
        for pipeline_name in pipeline_names:
            try:
                job_info = self.get_job_info(pipeline_name)
                last_build = job_info.get("lastBuild", {})
                last_successful = job_info.get("lastSuccessfulBuild", {})
                
                pipeline_status = {
                    "buildable": job_info.get("buildable", False),
                    "last_build_result": None,
                    "last_build_number": None,
                    "last_successful_build": None,
                    "health_score": 100,
                    "status": "HEALTHY"
                }
                
                if last_build:
                    build_info = self.get_build_info(pipeline_name, last_build.get("number"))
                    pipeline_status["last_build_result"] = build_info.get("result")
                    pipeline_status["last_build_number"] = build_info.get("number")
                    
                    # Determine health based on recent builds
                    if build_info.get("result") == "FAILURE":
                        pipeline_status["status"] = "UNHEALTHY"
                        pipeline_status["health_score"] = 0
                        unhealthy_count += 1
                    elif build_info.get("result") == "UNSTABLE":
                        pipeline_status["status"] = "WARNING"
                        pipeline_status["health_score"] = 50
                
                if last_successful:
                    pipeline_status["last_successful_build"] = last_successful.get("number")
                
                health_report["pipelines"][pipeline_name] = pipeline_status
                
            except Exception as e:
                health_report["pipelines"][pipeline_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "health_score": 0
                }
                unhealthy_count += 1
        
        # Overall status determination
        if unhealthy_count > len(pipeline_names) * 0.5:
            health_report["overall_status"] = "CRITICAL"
        elif unhealthy_count > 0:
            health_report["overall_status"] = "WARNING"
        
        return health_report
    
    def get_recent_failures(self, job_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent failed builds for analysis."""
        try:
            job_info = self.get_job_info(job_name)
            builds = job_info.get("builds", [])
            
            failures = []
            for build in builds[:limit * 3]:  # Check more builds to find failures
                build_info = self.get_build_info(job_name, build["number"])
                if build_info.get("result") == "FAILURE":
                    failures.append({
                        "build_number": build_info.get("number"),
                        "timestamp": build_info.get("timestamp"),
                        "duration": build_info.get("duration"),
                        "url": build_info.get("url"),
                        "actions": build_info.get("actions", [])
                    })
                    if len(failures) >= limit:
                        break
            
            return failures
        except Exception as e:
            return [{"error": str(e)}]

# Enhanced Tools
class JenkinsPipelineMonitorTool(AbstractTool):
    """Tool for monitoring pipeline status during incidents."""
    
    name: str = "jenkins_pipeline_monitor"
    description: str = (
        "Monitor Jenkins pipeline status with optional wait for completion. "
        "Essential for tracking deployment progress during incident response."
    )
    args_schema: Type[BaseModel] = PipelineStatusInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self,
        job_name: str,
        wait_for_completion: bool = False,
        timeout_seconds: int = 300,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        try:
            # Get current job status
            job_info = self.jenkins_client.get_job_info(job_name)
            last_build = job_info.get("lastBuild", {})
            
            result = {
                "job_name": job_name,
                "buildable": job_info.get("buildable", False),
                "last_build": last_build
            }
            
            # If waiting for completion and there's an active build
            if wait_for_completion and last_build:
                build_number = last_build.get("number")
                if build_number:
                    completion_result = self.jenkins_client.wait_for_build_completion(
                        job_name, build_number, timeout_seconds
                    )
                    result["completion_status"] = completion_result
            
            return json.dumps({"success": True, "result": result})
            
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

class JenkinsHealthCheckTool(AbstractTool):
    """Tool for checking overall CI/CD pipeline health."""
    
    name: str = "jenkins_health_check"
    description: str = (
        "Check health status of multiple Jenkins pipelines. "
        "Useful for getting overall CI/CD system health during incidents."
    )
    args_schema: Type[BaseModel] = HealthCheckInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self,
        pipeline_names: List[str],
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        try:
            health_report = self.jenkins_client.get_pipeline_health(pipeline_names)
            return json.dumps({"success": True, "health_report": health_report})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

class JenkinsEmergencyDeployTool(AbstractTool):
    """Tool for emergency deployments during incidents."""
    
    name: str = "jenkins_emergency_deploy"
    description: str = (
        "Trigger emergency deployment with specific branch/commit. "
        "Includes options to skip tests for faster deployment during critical incidents."
    )
    args_schema: Type[BaseModel] = EmergencyDeployInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self,
        job_name: str,
        branch_or_commit: str,
        environment: str,
        skip_tests: bool = False,
        reason: str = "",
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        try:
            parameters = {
                "BRANCH_OR_COMMIT": branch_or_commit,
                "ENVIRONMENT": environment,
                "SKIP_TESTS": str(skip_tests).lower(),
                "EMERGENCY_REASON": reason,
                "TRIGGERED_BY": "IncidentResponseAgent"
            }
            
            result = self.jenkins_client.trigger_build(job_name, parameters)
            
            return json.dumps({
                "success": True,
                "deployment_triggered": True,
                "job_name": job_name,
                "parameters": parameters,
                "result": result
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

class JenkinsRollbackTool(AbstractTool):
    """Tool for triggering rollback deployments."""
    
    name: str = "jenkins_rollback"
    description: str = (
        "Trigger rollback to a previous version. "
        "Critical for quickly reverting problematic deployments during incidents."
    )
    args_schema: Type[BaseModel] = RollbackInput
    
    def __init__(self, jenkins_client: JenkinsClient):
        super().__init__()
        self.jenkins_client = jenkins_client
    
    def _run(
        self,
        job_name: str,
        environment: str,
        target_version: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        try:
            parameters = {
                "ENVIRONMENT": environment,
                "ROLLBACK_ACTION": "true",
                "TRIGGERED_BY": "IncidentResponseAgent"
            }
            
            if target_version:
                parameters["TARGET_VERSION"] = target_version
            
            result = self.jenkins_client.trigger_build(job_name, parameters)
            
            return json.dumps({
                "success": True,
                "rollback_triggered": True,
                "job_name": job_name,
                "environment": environment,
                "target_version": target_version,
                "result": result
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
