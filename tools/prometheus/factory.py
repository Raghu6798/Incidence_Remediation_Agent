import os
from typing import List, Optional, Dict, Any,Type
from datetime import datetime, timedelta

from tools.prometheus.prometheus_tool import PrometheusTool,PrometheusToolBuilder,CommonQueries
from tools.base import AbstractTool, ToolInputSchema
from pydantic import BaseModel, Field


class ServiceHealthCheckSchema(ToolInputSchema):
    """Schema for service health checks."""
    service_name: str = Field(description="Name of the service to check")
    time_range: Optional[str] = Field(default="5m", description="Time range for health check (e.g., '5m', '1h')")


class PerformanceMetricsSchema(ToolInputSchema):
    """Schema for performance metrics queries."""
    metric_type: str = Field(description="Type of metric: 'cpu', 'memory', 'disk', 'network'")
    instance: Optional[str] = Field(default=None, description="Specific instance to check")
    time_range: Optional[str] = Field(default="15m", description="Time range for metrics")


class ErrorAnalysisSchema(ToolInputSchema):
    """Schema for error analysis."""
    service_name: str = Field(description="Service name to analyze for errors")
    error_threshold: Optional[float] = Field(default=5.0, description="Error rate threshold percentage")
    time_range: Optional[str] = Field(default="10m", description="Time range for error analysis")


class AlertInvestigationSchema(ToolInputSchema):
    """Schema for alert investigation."""
    alert_name: Optional[str] = Field(default=None, description="Specific alert name to investigate")
    severity: Optional[str] = Field(default=None, description="Alert severity: 'critical', 'warning', 'info'")


class CustomPrometheusQuerySchema(ToolInputSchema):
    """Schema for custom PromQL queries."""
    query: str = Field(description="Custom PromQL query")
    start_time: Optional[str] = Field(default=None, description="Start time for range query")
    end_time: Optional[str] = Field(default=None, description="End time for range query")
    step: Optional[str] = Field(default="15s", description="Query step interval")


class ServiceHealthChecker(AbstractTool):
    """Tool for checking service health and availability."""
    
    name: str = "check_service_health"
    description: str = """
    Check the health and availability of services. Useful for:
    - Verifying if services are up and running
    - Checking service response times
    - Monitoring service availability over time
    - Identifying service outages or degradation
    """
    args_schema :Type[BaseModel] = ServiceHealthCheckSchema
    
    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self.prometheus_tool = prometheus_tool
    
    def _run(self, service_name: str, time_range: str = "5m", **kwargs) -> str:
        """Check service health."""
        try:
            # Check service availability
            availability_query = CommonQueries.service_availability(service_name)
            availability_result = self.prometheus_tool._run(
                query=availability_query,
                start_time=time_range,
                end_time="now"
            )
            
            # Check response time if available
            response_time_query = f'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[{time_range}]))'
            response_time_result = self.prometheus_tool._run(
                query=response_time_query,
                start_time=time_range,
                end_time="now"
            )
            
            # Check request rate
            request_rate_query = CommonQueries.http_request_rate(service_name, time_range)
            request_rate_result = self.prometheus_tool._run(
                query=request_rate_query,
                start_time=time_range,
                end_time="now"
            )
            
            return f"""
Service Health Report for: {service_name}
Time Range: {time_range}

=== AVAILABILITY ===
{availability_result}

=== RESPONSE TIME (95th percentile) ===
{response_time_result}

=== REQUEST RATE ===
{request_rate_result}
"""
        except Exception as e:
            return f"Error checking service health for {service_name}: {str(e)}"


class PerformanceAnalyzer(AbstractTool):
    """Tool for analyzing system and application performance metrics."""
    
    name: str = "analyze_performance"
    description: str = """
    Analyze system and application performance metrics. Useful for:
    - CPU utilization analysis
    - Memory usage monitoring
    - Disk I/O performance
    - Network traffic analysis
    - Resource bottleneck identification
    """
    args_schema :Type[BaseModel] = PerformanceMetricsSchema
    
    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self.prometheus_tool = prometheus_tool
    
    def _run(self, metric_type: str, instance: Optional[str] = None, time_range: str = "15m", **kwargs) -> str:
        """Analyze performance metrics."""
        try:
            if metric_type.lower() == "cpu":
                query = CommonQueries.cpu_usage(instance)
                metric_name = "CPU Usage"
            elif metric_type.lower() == "memory":
                query = CommonQueries.memory_usage(instance)
                metric_name = "Memory Usage"
            elif metric_type.lower() == "disk":
                filter_clause = f'{{instance="{instance}"}}' if instance else ""
                query = f'rate(node_disk_read_bytes_total{filter_clause}[{time_range}]) + rate(node_disk_written_bytes_total{filter_clause}[{time_range}])'
                metric_name = "Disk I/O"
            elif metric_type.lower() == "network":
                filter_clause = f'{{instance="{instance}"}}' if instance else ""
                query = f'rate(node_network_receive_bytes_total{filter_clause}[{time_range}]) + rate(node_network_transmit_bytes_total{filter_clause}[{time_range}])'
                metric_name = "Network Traffic"
            else:
                return f"Unsupported metric type: {metric_type}. Supported types: cpu, memory, disk, network"
            
            result = self.prometheus_tool._run(
                query=query,
                start_time=time_range,
                end_time="now"
            )
            
            return f"""
Performance Analysis Report
Metric: {metric_name}
Instance: {instance or "All instances"}
Time Range: {time_range}

{result}
"""
        except Exception as e:
            return f"Error analyzing {metric_type} performance: {str(e)}"


class ErrorAnalyzer(AbstractTool):
    """Tool for analyzing errors and failure rates."""
    
    name: str = "analyze_errors"
    description: str = """
    Analyze error rates and failure patterns. Useful for:
    - HTTP error rate analysis (4xx, 5xx responses)
    - Application error tracking
    - Failure pattern identification
    - Error threshold monitoring
    - SLA compliance checking
    """
    args_schema :Type[BaseModel] = ErrorAnalysisSchema
    
    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self.prometheus_tool = prometheus_tool
    
    def _run(self, service_name: str, error_threshold: float = 5.0, time_range: str = "10m", **kwargs) -> str:
        """Analyze error rates and patterns."""
        try:
            # Overall error rate
            error_rate_query = CommonQueries.error_rate(service_name, time_range)
            error_rate_result = self.prometheus_tool._run(
                query=error_rate_query,
                start_time=time_range,
                end_time="now"
            )
            
            # 4xx errors
            client_error_query = f'sum(rate(http_requests_total{{service="{service_name}", status=~"4.."}}[{time_range}])) / sum(rate(http_requests_total{{service="{service_name}"}}[{time_range}])) * 100'
            client_error_result = self.prometheus_tool._run(
                query=client_error_query,
                start_time=time_range,
                end_time="now"
            )
            
            # 5xx errors
            server_error_query = f'sum(rate(http_requests_total{{service="{service_name}", status=~"5.."}}[{time_range}])) / sum(rate(http_requests_total{{service="{service_name}"}}[{time_range}])) * 100'
            server_error_result = self.prometheus_tool._run(
                query=server_error_query,
                start_time=time_range,
                end_time="now"
            )
            
            # Top error endpoints
            top_errors_query = f'topk(5, sum by (endpoint) (rate(http_requests_total{{service="{service_name}", status=~"[45].."}}[{time_range}])))'
            top_errors_result = self.prometheus_tool._run(
                query=top_errors_query,
                start_time=time_range,
                end_time="now"
            )
            
            return f"""
Error Analysis Report for: {service_name}
Time Range: {time_range}
Error Threshold: {error_threshold}%

=== OVERALL ERROR RATE ===
{error_rate_result}

=== CLIENT ERRORS (4xx) ===
{client_error_result}

=== SERVER ERRORS (5xx) ===
{server_error_result}

=== TOP ERROR ENDPOINTS ===
{top_errors_result}
"""
        except Exception as e:
            return f"Error analyzing errors for {service_name}: {str(e)}"


class AlertInvestigator(AbstractTool):
    """Tool for investigating active alerts and their causes."""
    
    name: str = "investigate_alerts"
    description: str = """
    Investigate active alerts and their root causes. Useful for:
    - Viewing currently firing alerts
    - Understanding alert severity and impact
    - Correlating alerts with metrics
    - Alert escalation analysis
    - Historical alert patterns
    """
    args_schema :Type[BaseModel] = AlertInvestigationSchema
    
    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self.prometheus_tool = prometheus_tool
    
    def _run(self, alert_name: Optional[str] = None, severity: Optional[str] = None, **kwargs) -> str:
        """Investigate alerts."""
        try:
            # Base query for alerts
            if alert_name:
                alerts_query = f'ALERTS{{alertname="{alert_name}"}}'
            elif severity:
                alerts_query = f'ALERTS{{severity="{severity}"}}'
            else:
                alerts_query = 'ALERTS{alertstate="firing"}'
            
            alerts_result = self.prometheus_tool._run(query=alerts_query)
            
            # Alert summary by severity
            alert_summary_query = 'sum by (severity) (ALERTS{alertstate="firing"})'
            alert_summary_result = self.prometheus_tool._run(query=alert_summary_query)
            
            # Most frequent alerts
            frequent_alerts_query = 'topk(10, count by (alertname) (ALERTS{alertstate="firing"}))'
            frequent_alerts_result = self.prometheus_tool._run(query=frequent_alerts_query)
            
            return f"""
Alert Investigation Report
Alert Name Filter: {alert_name or "All alerts"}
Severity Filter: {severity or "All severities"}

=== CURRENT ALERTS ===
{alerts_result}

=== ALERT SUMMARY BY SEVERITY ===
{alert_summary_result}

=== MOST FREQUENT ALERTS ===
{frequent_alerts_result}
"""
        except Exception as e:
            return f"Error investigating alerts: {str(e)}"


class CustomQueryTool(AbstractTool):
    """Tool for executing custom PromQL queries."""
    
    name: str = "custom_prometheus_query"
    description: str = """
    Execute custom PromQL queries for advanced monitoring. Useful for:
    - Custom metric analysis
    - Complex aggregations
    - Advanced troubleshooting
    - Custom dashboards
    - Specific monitoring requirements
    """
    args_schema :Type[BaseModel] = CustomPrometheusQuerySchema
    
    def __init__(self, prometheus_tool: PrometheusTool):
        super().__init__()
        self.prometheus_tool = prometheus_tool
    
    def _run(self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None, step: str = "15s", **kwargs) -> str:
        """Execute custom PromQL query."""
        try:
            result = self.prometheus_tool._run(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            
            return f"""
Custom Query Results
Query: {query}
Time Range: {start_time or 'instant'} to {end_time or 'now'}
Step: {step}

{result}
"""
        except Exception as e:
            return f"Error executing custom query: {str(e)}"


class PrometheusToolsetFactory:
    """Factory for creating a comprehensive set of Prometheus tools."""
    
    @staticmethod
    def create_incident_response_toolset(
        prometheus_url: str = "http://localhost:9090",
        username: Optional[str] = None,
        password: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None
    ) -> List[AbstractTool]:
        """Create a comprehensive set of Prometheus tools for incident response."""
        
        # Create base Prometheus tool
        base_tool = PrometheusToolBuilder.create_tool(
            prometheus_url=prometheus_url,
            username=username,
            password=password,
            custom_headers=headers
        )
        
        # Create specialized tools
        tools = [
            ServiceHealthChecker(base_tool),
            PerformanceAnalyzer(base_tool),
            ErrorAnalyzer(base_tool),
            AlertInvestigator(base_tool),
            CustomQueryTool(base_tool),
            base_tool  # Include the original tool for backward compatibility
        ]
        
        return tools
    
    @staticmethod
    def create_toolset_from_env() -> List[AbstractTool]:
        """Create toolset from environment variables."""
        url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
        username = os.environ.get("PROMETHEUS_USERNAME")
        password = os.environ.get("PROMETHEUS_PASSWORD")
        
        headers = {}
        headers_str = os.environ.get("PROMETHEUS_HEADERS")
        if headers_str:
            import json
            try:
                headers = json.loads(headers_str)
            except Exception:
                headers = {}
        
        return PrometheusToolsetFactory.create_incident_response_toolset(
            prometheus_url=url,
            username=username,
            password=password,
            headers=headers or None
        )