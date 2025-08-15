import os
import asyncio
from typing import List, Optional, Dict, Any, Type

# Assuming these imports are in your project structure
from tools.prometheus.prometheus_tool import (
    PrometheusTool,
    PrometheusToolBuilder,
    CommonQueries,
)
from tools.base import AbstractTool, ToolInputSchema
from pydantic import BaseModel, Field, PrivateAttr


class ServiceHealthCheckSchema(ToolInputSchema):
    """Schema for service health checks."""
    service_name: str = Field(description="Name of the service (job label in Prometheus) to check")
    time_range: Optional[str] = Field(
        default="5m", description="Time range for health check (e.g., '5m', '1h')"
    )


class PerformanceMetricsSchema(ToolInputSchema):
    """Schema for performance metrics queries."""
    metric_type: str = Field(
        description="Type of metric: 'cpu', 'memory', 'disk', 'network'"
    )
    instance: Optional[str] = Field(
        default=None, description="Specific instance to check (e.g., 'fastapi-app:8000')"
    )
    time_range: Optional[str] = Field(
        default="15m", description="Time range for metrics"
    )


class ErrorAnalysisSchema(ToolInputSchema):
    """Schema for error analysis."""
    service_name: str = Field(description="Service name (job label) to analyze for errors")
    time_range: Optional[str] = Field(
        default="10m", description="Time range for error analysis"
    )


class AlertInvestigationSchema(ToolInputSchema):
    """Schema for alert investigation."""
    alert_name: Optional[str] = Field(
        default=None, description="Specific alert name to investigate"
    )
    severity: Optional[str] = Field(
        default=None, description="Alert severity: 'critical', 'warning', 'info'"
    )


class CustomPrometheusQuerySchema(ToolInputSchema):
    """Schema for custom PromQL queries."""
    query: str = Field(description="Custom PromQL query")


class ServiceHealthChecker(AbstractTool):
    """Tool for checking service health and availability."""
    name: str = "check_service_health"
    description: str = "Checks the health, availability, response time, and request rate of a service using its job name."
    args_schema: Type[BaseModel] = ServiceHealthCheckSchema
    _prometheus_tool: PrometheusTool = PrivateAttr()

    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self._prometheus_tool = prometheus_tool

    def _run(self, service_name: str, time_range: str = "5m", **kwargs) -> str:
        """Check service health."""
        try:
            availability_query = CommonQueries.service_availability(service_name)
            availability_result = self._prometheus_tool._run(query=availability_query)

            response_time_query = f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="{service_name}"}}[{time_range}])) by (le))'
            response_time_result = self._prometheus_tool._run(query=response_time_query)
            
            # FIX: Use a more robust sum() query for request rate to avoid "no data" issues.
            request_rate_query = f'sum(rate(http_requests_total{{job="{service_name}"}}[{time_range}]))'
            request_rate_result = self._prometheus_tool._run(query=request_rate_query)

            return f"""Service Health Report for: {service_name} (Time Range: last {time_range})
=== AVAILABILITY (up == 1) ===
{availability_result}

=== 95th Percentile Response Time (seconds) ===
{response_time_result}

=== Request Rate (requests/sec) ===
{request_rate_result}"""
        except Exception as e:
            return f"Error checking service health for {service_name}: {str(e)}"

    async def _arun(self, service_name: str, time_range: str = "5m", **kwargs) -> str:
        return await asyncio.to_thread(
            self._run, service_name=service_name, time_range=time_range, **kwargs
        )


class PerformanceAnalyzer(AbstractTool):
    """Tool for analyzing system and application performance metrics."""
    name: str = "analyze_performance"
    description: str = (
        "Analyzes low-level system resource usage for a specific scraped target. "
        "This tool is for investigating the underlying infrastructure, NOT the application logic. "
        "It requires the `instance` label of the target (e.g., 'localhost:9090'). "
        "Valid `metric_type` options are: 'cpu', 'memory', 'disk', and 'network'."
    )
    args_schema: Type[BaseModel] = PerformanceMetricsSchema
    _prometheus_tool: PrometheusTool = PrivateAttr()

    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self._prometheus_tool = prometheus_tool

    def _run(
        self, metric_type: str, instance: Optional[str] = None, time_range: str = "15m", **kwargs
    ) -> str:
        """Analyze performance metrics."""
        try:
            metric_type = metric_type.lower()
            filter_clause = f'instance="{instance}"' if instance else ""
            
            if metric_type == "cpu":
                # FIX: Build the query directly to handle the time_range correctly.
                # This query is for node_exporter CPU usage.
                query = f'(1 - avg(rate(node_cpu_seconds_total{{mode="idle", {filter_clause}}}[{time_range}]))) * 100'
                metric_name = "CPU Usage (%)"
            elif metric_type == "memory":
                # FIX: Pass only the instance to the CommonQueries helper, as it's a gauge.
                query = CommonQueries.memory_usage(instance)
                metric_name = "Memory Usage (%)"
            elif metric_type == "disk":
                query = f"rate(node_disk_read_bytes_total{{{filter_clause}}}[{time_range}]) + rate(node_disk_written_bytes_total{{{filter_clause}}}[{time_range}])"
                metric_name = "Disk I/O (bytes/sec)"
            elif metric_type == "network":
                query = f"rate(node_network_receive_bytes_total{{{filter_clause}}}[{time_range}]) + rate(node_network_transmit_bytes_total{{{filter_clause}}}[{time_range}])"
                metric_name = "Network Traffic (bytes/sec)"
            else:
                return f"Unsupported metric type: {metric_type}. Supported types are: cpu, memory, disk, network"

            result = self._prometheus_tool._run(query=query)
            return f"""Performance Analysis Report
Metric: {metric_name}
Instance: {instance or "All instances"}
Time Range: last {time_range}

{result}"""
        except Exception as e:
            return f"Error analyzing {metric_type} performance: {str(e)}"

    async def _arun(
        self, metric_type: str, instance: Optional[str] = None, time_range: str = "15m", **kwargs
    ) -> str:
        return await asyncio.to_thread(
            self._run, metric_type=metric_type, instance=instance, time_range=time_range, **kwargs
        )


class ErrorAnalyzer(AbstractTool):
    """Tool for analyzing errors and failure rates."""
    name: str = "analyze_errors"
    description: str = (
        "Analyzes the rate of HTTP errors for a specific application service using its Prometheus `job` name. "
        "Use this to quantify the impact of an incident or to identify which types of errors (client-side 4xx vs. server-side 5xx) are occurring. "
        "It also identifies the top 5 URL paths that are returning errors."
    )
    args_schema: Type[BaseModel] = ErrorAnalysisSchema
    _prometheus_tool: PrometheusTool = PrivateAttr()

    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self._prometheus_tool = prometheus_tool

    def _run(self, service_name: str, time_range: str = "10m", **kwargs) -> str:
        """Analyze error rates and patterns."""
        try:
            error_rate_query = CommonQueries.error_rate(service_name, time_range)
            error_rate_result = self._prometheus_tool._run(query=error_rate_query)

            client_error_query = f'sum(rate(http_requests_total{{job="{service_name}", code=~"4.."}}[{time_range}]))'
            client_error_result = self._prometheus_tool._run(query=client_error_query)

            server_error_query = f'sum(rate(http_requests_total{{job="{service_name}", code=~"5.."}}[{time_range}]))'
            server_error_result = self._prometheus_tool._run(query=server_error_query)

            top_errors_query = f'topk(5, sum by (path) (rate(http_requests_total{{job="{service_name}", code=~"[45].."}}[{time_range}])))'
            top_errors_result = self._prometheus_tool._run(query=top_errors_query)

            return f"""Error Analysis Report for: {service_name} (Time Range: last {time_range})
=== Overall Error Rate (% of all requests) ===
{error_rate_result}

=== Client Errors (4xx rate) ===
{client_error_result}

=== Server Errors (5xx rate) ===
{server_error_result}

=== Top 5 Erroring URL Paths ===
{top_errors_result}"""
        except Exception as e:
            return f"Error analyzing errors for {service_name}: {str(e)}"

    async def _arun(self, service_name: str, time_range: str = "10m", **kwargs) -> str:
        return await asyncio.to_thread(
            self._run, service_name=service_name, time_range=time_range, **kwargs
        )


class AlertInvestigator(AbstractTool):
    """Tool for investigating active alerts."""
    name: str = "investigate_alerts"
    description: str = (
        "Investigates the alerts that are currently in a 'firing' state in Prometheus Alertmanager. "
        "Use this to get a quick overview of what Prometheus considers to be an active problem in the environment. "
        "You can optionally filter by `alert_name` or `severity` (e.g., 'critical', 'warning')."
    )
    args_schema: Type[BaseModel] = AlertInvestigationSchema
    _prometheus_tool: PrometheusTool = PrivateAttr()

    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self._prometheus_tool = prometheus_tool

    def _run(self, alert_name: Optional[str] = None, severity: Optional[str] = None, **kwargs) -> str:
        """Investigate alerts."""
        try:
            if alert_name:
                alerts_query = f'ALERTS{{alertname="{alert_name}", alertstate="firing"}}'
            elif severity:
                alerts_query = f'ALERTS{{severity="{severity}", alertstate="firing"}}'
            else:
                alerts_query = 'ALERTS{alertstate="firing"}'
            alerts_result = self._prometheus_tool._run(query=alerts_query)

            alert_summary_query = 'sum by (severity) (ALERTS{alertstate="firing"})'
            alert_summary_result = self._prometheus_tool._run(query=alert_summary_query)

            return f"""Alert Investigation Report
Filter: alert_name='{alert_name or "any"}', severity='{severity or "any"}'

=== Currently Firing Alerts ===
{alerts_result}

=== Firing Alert Summary by Severity ===
{alert_summary_result}"""
        except Exception as e:
            return f"Error investigating alerts: {str(e)}"

    async def _arun(
        self, alert_name: Optional[str] = None, severity: Optional[str] = None, **kwargs
    ) -> str:
        return await asyncio.to_thread(
            self._run, alert_name=alert_name, severity=severity, **kwargs
        )


class CustomQueryTool(AbstractTool):
    """Tool for executing custom PromQL queries."""
    name: str = "custom_prometheus_query"
    description: str = (
        "Executes a raw PromQL (Prometheus Query Language) query. "
        "This is an expert-level tool. You should ALWAYS prefer to use one of the specialized tools first "
        "(`check_service_health`, `analyze_performance`, `analyze_errors`). "
        "Only use this tool if the other tools cannot provide the specific information you need."
    )
    args_schema: Type[BaseModel] = CustomPrometheusQuerySchema
    _prometheus_tool: PrometheusTool = PrivateAttr()

    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self._prometheus_tool = prometheus_tool

    def _run(self, query: str, **kwargs) -> str:
        """Execute custom PromQL query."""
        try:
            result = self._prometheus_tool._run(query=query)
            return f"""Custom Query Result for:
'{query}'

{result}"""
        except Exception as e:
            return f"Error executing custom query: {str(e)}"

    async def _arun(self, query: str, **kwargs) -> str:
        return await asyncio.to_thread(self._run, query=query, **kwargs)


class PrometheusToolsetFactory:
    """Factory for creating a comprehensive set of Prometheus tools."""

    @staticmethod
    def create_incident_response_toolset(
        prometheus_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> List[AbstractTool]:
        """Create a comprehensive set of Prometheus tools for incident response."""
        base_tool = PrometheusToolBuilder.create_tool(
            prometheus_url=prometheus_url,
            username=username,
            password=password,
            custom_headers=headers,
        )

        tools = [
            ServiceHealthChecker(base_tool),
            PerformanceAnalyzer(base_tool),
            ErrorAnalyzer(base_tool),
            AlertInvestigator(base_tool),
            CustomQueryTool(base_tool),
        ]
        return tools

    @staticmethod
    def create_toolset_from_env() -> List[AbstractTool]:
        """Create toolset from environment variables."""
        url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
        username = os.environ.get("PROMETHEUS_USERNAME")
        password = os.environ.get("PROMETHEUS_PASSWORD")
        headers_str = os.environ.get("PROMETHEUS_HEADERS")
        headers = {}
        if headers_str:
            import json
            try:
                headers = json.loads(headers_str)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode PROMETHEUS_HEADERS JSON string: {headers_str}")
                headers = {}

        return PrometheusToolsetFactory.create_incident_response_toolset(
            prometheus_url=url,
            username=username,
            password=password,
            headers=headers or None,
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    from pydantic import ValidationError

    load_dotenv()

    print("🚀 Starting Prometheus Tool Manual Test Suite (LangChain `.invoke()` method)...")
    print("-" * 50)

    # --- Configuration ---
    # Set these values to match a service that is actively being scraped by your Prometheus.
    TEST_SERVICE_NAME = "fastapi-app"
    TEST_INSTANCE = "fastapi-app:8000"
    
    prometheus_url = os.getenv("PROMETHEUS_URL")
    if not prometheus_url:
        print("❌ FATAL: PROMETHEUS_URL environment variable is not set. Exiting.")
        exit(1)
        
    print(f"✅ Using Prometheus URL: {prometheus_url}")
    print(f"✅ Using Test Service Name: '{TEST_SERVICE_NAME}'")
    print(f"✅ Using Test Instance: '{TEST_INSTANCE}'")
    print("-" * 50)

    try:
        print("🛠️  Initializing Prometheus toolset...")
        all_prometheus_tools = PrometheusToolsetFactory.create_toolset_from_env()
        tools_by_name = {tool.name: tool for tool in all_prometheus_tools}
        print(f"✅ Successfully initialized {len(all_prometheus_tools)} tools.")
        print("-" * 50)

        # --- Test Cases using .invoke() ---

        # 1. Test ServiceHealthChecker
        print("\n🧪 Testing 'check_service_health' Tool...")
        health_checker = tools_by_name.get("check_service_health")
        if health_checker:
            health_input = {"service_name": TEST_SERVICE_NAME, "time_range": "1m"}
            print(f"  Input: {health_input}")
            health_result = health_checker.invoke(health_input)
            print("--- Health Check Result ---")
            print(health_result)
            print("---------------------------\n")

        # 2. Test PerformanceAnalyzer
        print("\n🧪 Testing 'analyze_performance' Tool (CPU)...")
        perf_analyzer = tools_by_name.get("analyze_performance")
        if perf_analyzer:
            cpu_input = {"metric_type": "cpu", "instance": TEST_INSTANCE, "time_range": "1m"}
            print(f"  Input: {cpu_input}")
            cpu_result = perf_analyzer.invoke(cpu_input)
            print("--- CPU Performance Result ---")
            print(cpu_result)
            print("------------------------------\n")
            
        # 3. Test CustomQueryTool
        print("\n🧪 Testing 'custom_prometheus_query' Tool...")
        custom_query_tool = tools_by_name.get("custom_prometheus_query")
        if custom_query_tool:
            query_input = {'query': f'up{{job="{TEST_SERVICE_NAME}"}}'}
            print(f"  Input: {query_input}")
            custom_result = custom_query_tool.invoke(query_input)
            print("--- Custom Query Result ---")
            print(custom_result)
            print("---------------------------\n")

        # 4. DEMONSTRATE VALIDATION: Test a tool with INVALID input
        print("\n🧪 Demonstrating Validation Error...")
        if health_checker:
            invalid_input = {"time_range": "5m"}
            print(f"  Attempting to invoke with invalid input: {invalid_input}")
            try:
                health_checker.invoke(invalid_input)
            except ValidationError as e:
                print(f"✅ SUCCESS: Tool correctly raised a ValidationError as expected.")
                print(f"   Error details: {e}")

        print("\n" + "=" * 50)
        print("✅ All tests completed.")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ An error occurred during the test suite: {e}")
        import traceback
        traceback.print_exc()