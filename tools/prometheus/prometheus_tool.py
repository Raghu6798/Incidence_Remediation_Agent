import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any,Type, Tuple
from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
import aiohttp

from tools.base import AbstractTool, ToolInputSchema


class PrometheusQuerySchema(ToolInputSchema):
    """Input schema for Prometheus queries."""

    query: str = Field(description="PromQL query string to execute against Prometheus")
    start_time: Optional[str] = Field(
        default=None,
        description="Start time in ISO format (e.g., '2024-01-01T00:00:00Z') or relative (e.g., '1h', '30m')",
    )
    end_time: Optional[str] = Field(
        default=None, description="End time in ISO format or 'now' for current time"
    )
    step: Optional[str] = Field(
        default="15s",
        description="Query resolution step width (e.g., '15s', '1m', '5m')",
    )
    timeout: Optional[int] = Field(default=30, description="Query timeout in seconds")


class PrometheusTool(AbstractTool):
    """LangChain tool for querying Prometheus metrics."""

    name: str = "prometheus_query"
    description: str = """
    Query Prometheus metrics using PromQL. Useful for:
    - Monitoring system performance and health
    - Retrieving application metrics
    - Analyzing infrastructure metrics
    - Getting alerts and thresholds data
    
    Examples of useful queries:
    - up: Check service availability
    - rate(http_requests_total[5m]): HTTP request rate
    - cpu_usage_percent: CPU utilization
    - memory_usage_bytes: Memory consumption
    """
    args_schema: Type[BaseModel] = PrometheusQuerySchema

    # === DECLARED FIELDS (FIX) ===
    # All attributes must be declared as fields for Pydantic validation.
    prometheus_url: str
    auth: Optional[Tuple[str, str]] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    # === CORRECTED __init__ METHOD (FIX) ===
    # This pattern correctly initializes a Pydantic-based class with custom logic.
    def __init__(
        self,
        prometheus_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        # 1. Prepare the values for the fields.
        auth_tuple = (username, password) if username and password else None
        headers_dict = headers or {}

        # 2. Pass all prepared values to the parent constructor for validation and assignment.
        super().__init__(
            prometheus_url=prometheus_url.rstrip("/"),
            auth=auth_tuple,
            headers=headers_dict,
            **kwargs,
        )

    def _parse_time(self, time_str: Optional[str]) -> Optional[str]:
        """Parse time string to appropriate format for Prometheus."""
        if not time_str:
            return None
        if time_str == "now":
            return datetime.utcnow().isoformat() + "Z"
        if time_str.endswith(("s", "m", "h", "d")):
            return time_str
        return time_str

    def _build_query_params(self, **kwargs) -> Tuple[Dict[str, Any], str]:
        """Build query parameters for Prometheus API."""
        params = {"query": kwargs["query"]}
        start_time = self._parse_time(kwargs.get("start_time"))
        end_time = self._parse_time(kwargs.get("end_time"))

        if start_time and end_time:
            # Range query
            params.update(
                {
                    "start": start_time,
                    "end": end_time,
                    "step": kwargs.get("step", "15s"),
                }
            )
            endpoint = "query_range"
        else:
            # Instant query
            if end_time:
                params["time"] = end_time
            endpoint = "query"

        return params, endpoint

    def _format_response(self, response_data: Dict[str, Any]) -> str:
        """Format Prometheus response for better readability."""
        if response_data.get("status") != "success":
            return f"Error: {response_data.get('error', 'Unknown error')}"

        data = response_data.get("data", {})
        result_type = data.get("resultType")
        results = data.get("result", [])

        if not results:
            return "No data found for the given query."

        formatted_results = []
        for result in results:
            metric_name = result.get("metric", {})
            if result_type == "matrix":
                values = result.get("values", [])
                metric_info = f"Metric: {metric_name}"
                if values:
                    sample_str = str(values[:3])
                    formatted_results.append(
                        f"{metric_info}\nSample values: {sample_str}{'...' if len(values) > 3 else ''}"
                    )
                else:
                    formatted_results.append(f"{metric_info}\nNo values")
            elif result_type == "vector":
                value = result.get("value", [])
                if len(value) >= 2:
                    timestamp, val = value[0], value[1]
                    formatted_results.append(
                        f"Metric: {metric_name}\nValue: {val} (at {datetime.fromtimestamp(float(timestamp))})"
                    )
            elif result_type == "scalar":
                value = result.get("value", [])
                if len(value) >= 2:
                    formatted_results.append(
                        f"Scalar value: {value[1]} (at {datetime.fromtimestamp(float(value[0]))})"
                    )

        return (
            "\n\n".join(formatted_results)
            if formatted_results
            else "No results to display."
        )

    def _run(
        self, run_manager: Optional[CallbackManagerForToolRun] = None, **kwargs
    ) -> str:
        """Execute Prometheus query synchronously."""
        try:
            params, endpoint = self._build_query_params(**kwargs)
            url = f"{self.prometheus_url}/api/v1/{endpoint}"

            if run_manager:
                run_manager.on_text(f"Querying Prometheus: {params['query']}\n")

            response = requests.get(
                url,
                params=params,
                auth=self.auth,
                headers=self.headers,
                timeout=kwargs.get("timeout", 30),
            )
            response.raise_for_status()
            response_data = response.json()
            return self._format_response(response_data)
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Prometheus: {str(e)}"
        except json.JSONDecodeError:
            return f"Error parsing Prometheus response. Response text: {response.text}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    async def _arun(
        self, run_manager: Optional[AsyncCallbackManagerForToolRun] = None, **kwargs
    ) -> str:
        """Execute Prometheus query asynchronously."""
        try:
            params, endpoint = self._build_query_params(**kwargs)
            url = f"{self.prometheus_url}/api/v1/{endpoint}"

            if run_manager:
                await run_manager.on_text(f"Querying Prometheus: {params['query']}\n")

            async with aiohttp.ClientSession() as session:
                auth = (
                    aiohttp.BasicAuth(self.auth[0], self.auth[1]) if self.auth else None
                )
                async with session.get(
                    url,
                    params=params,
                    auth=auth,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=kwargs.get("timeout", 30)),
                ) as response:
                    response.raise_for_status()
                    response_data = await response.json()
            return self._format_response(response_data)
        except aiohttp.ClientError as e:
            return f"Error connecting to Prometheus: {str(e)}"
        except json.JSONDecodeError as e:
            return f"Error parsing Prometheus response: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"


class PrometheusToolBuilder:
    """Builder class to easily create configured Prometheus tools."""

    @staticmethod
    def create_tool(
        prometheus_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> PrometheusTool:
        """Create a configured Prometheus tool."""
        return PrometheusTool(
            prometheus_url=prometheus_url,
            username=username,
            password=password,
            headers=custom_headers,
        )

    @staticmethod
    def create_tool_from_config(config: Dict[str, Any]) -> PrometheusTool:
        """Create tool from configuration dictionary."""
        return PrometheusTool(
            prometheus_url=config["url"],
            username=config.get("username"),
            password=config.get("password"),
            headers=config.get("headers"),
        )


class CommonQueries:
    """Collection of commonly used PromQL queries."""

    @staticmethod
    def service_availability(service_name: str) -> str:
        return f'up{{job="{service_name}"}}'

    @staticmethod
    def cpu_usage(instance: Optional[str] = None) -> str:
        filter_clause = f'{{instance="{instance}"}}' if instance else ""
        return f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle"}}{filter_clause}[5m])) * 100)'

    @staticmethod
    def memory_usage(instance: Optional[str] = None) -> str:
        filter_clause = f'{{instance="{instance}"}}' if instance else ""
        return f"(1 - (node_memory_MemAvailable_bytes{filter_clause} / node_memory_MemTotal_bytes{filter_clause})) * 100"

    @staticmethod
    def http_request_rate(service: str, time_window: str = "5m") -> str:
        return f'rate(http_requests_total{{service="{service}"}}[{time_window}])'

    @staticmethod
    def error_rate(service: str, time_window: str = "5m") -> str:
        return f'sum(rate(http_requests_total{{service="{service}", status=~"5.."}}[{time_window}])) / sum(rate(http_requests_total{{service="{service}"}}[{time_window}])) * 100'


# Example initialization when the script is run directly
if __name__ == "__main__":
    # Create Prometheus tool
    prometheus_tool = PrometheusToolBuilder.create_tool(
        prometheus_url="http://localhost:9090"
    )

    # Example query
    print("Executing example query...")
    result = prometheus_tool.invoke({
    "query": CommonQueries.service_availability("prometheus"),
    "timeout": 10
})
    print("\n--- Query Result ---")
    print(result)
    print("--------------------")
