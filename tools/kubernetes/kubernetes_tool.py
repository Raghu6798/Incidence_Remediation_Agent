from typing import Optional, Type, List, Dict
from pydantic import BaseModel, Field
from kubernetes import client, config
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from tools.base import AbstractTool, ToolInputSchema
from datetime import datetime, timezone
import asyncio


# --- Utility Functions ---
def _calculate_age(creation_timestamp):
    """Calculates the age of a Kubernetes resource."""
    if not creation_timestamp:
        return "N/A"
    now = datetime.now(timezone.utc)
    age = now - creation_timestamp
    if age.days > 0:
        return f"{age.days}d"
    elif (age.seconds // 3600) > 0:
        return f"{age.seconds // 3600}h"
    elif (age.seconds // 60) > 0:
        return f"{age.seconds // 60}m"
    else:
        return f"{age.seconds}s"


# --- Base Kubernetes Tool ---
class BaseKubernetesTool(AbstractTool):
    """Base class for all Kubernetes tools to handle config loading."""

    api_client: client.ApiClient = Field(default=None, exclude=True)

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        context: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if not self.api_client:
            # Load config and context, then create a single reusable ApiClient
            config.load_kube_config(config_file=kubeconfig_path, context=context)
            self.api_client = client.ApiClient()


# --- Input Schemas ---
class ListPodsInputSchema(ToolInputSchema):
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace. If not provided, lists from all namespaces.",
    )


class ListServicesInputSchema(ToolInputSchema):
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace. If not provided, lists from all namespaces.",
    )


class ListDeploymentsInputSchema(ToolInputSchema):
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace. If not provided, lists from all namespaces.",
    )


class ListNodesInputSchema(ToolInputSchema):
    label_selector: Optional[str] = Field(
        default=None,
        description="Label selector to filter nodes. Example: 'node-role.kubernetes.io/worker=true'",
    )


class GetPodLogsInputSchema(ToolInputSchema):
    namespace: str = Field(description="Kubernetes namespace of the pod")
    pod_name: str = Field(description="Name of the pod to get logs from")
    container: Optional[str] = Field(
        default=None, description="Container name if pod has multiple containers"
    )
    tail_lines: Optional[int] = Field(
        default=100, description="Number of lines to return from the end of logs"
    )
    previous: Optional[bool] = Field(
        default=False, description="Get logs from previous container instance"
    )


class ScaleDeploymentInputSchema(ToolInputSchema):
    namespace: str = Field(description="Kubernetes namespace of the deployment")
    deployment_name: str = Field(description="Name of the deployment to scale")
    replicas: int = Field(description="Number of replicas to scale to")


class CreateNamespaceInputSchema(ToolInputSchema):
    name: str = Field(description="Name of the namespace to create")
    labels: Optional[Dict[str, str]] = Field(
        default=None, description="Labels to apply to the namespace"
    )


class DeletePodInputSchema(ToolInputSchema):
    namespace: str = Field(description="Kubernetes namespace of the pod")
    pod_name: str = Field(description="Name of the pod to delete")
    grace_period: Optional[int] = Field(
        default=30, description="Grace period in seconds before deletion"
    )


class GetServiceInputSchema(ToolInputSchema):
    namespace: str = Field(description="Kubernetes namespace of the service")
    service_name: str = Field(description="Name of the service to get details for")


class ListConfigMapsInputSchema(ToolInputSchema):
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace. If not provided, lists from all namespaces.",
    )


class ListSecretsInputSchema(ToolInputSchema):
    namespace: Optional[str] = Field(
        default=None,
        description="Kubernetes namespace. If not provided, lists from all namespaces.",
    )


# --- Tool Implementations ---


class ListPodsTool(BaseKubernetesTool):
    name: str = "list_k8s_pods"
    description: str = (
        "List pods in a Kubernetes cluster, optionally filtered by namespace."
    )
    args_schema: Type[BaseModel] = ListPodsInputSchema

    def _run(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            ret = (
                v1.list_namespaced_pod(namespace=namespace, watch=False)
                if namespace
                else v1.list_pod_for_all_namespaces(watch=False)
            )
            pods = [
                f"{i.status.pod_ip}\t{i.metadata.namespace}\t{i.metadata.name}"
                for i in ret.items
            ]
            return (
                "Pod IP\tNamespace\tName\n" + "\n".join(pods)
                if pods
                else "No pods found."
            )
        except Exception as e:
            return f"Error listing pods: {e}"

    async def _arun(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, namespace=namespace, run_manager=run_manager, **kwargs
        )


class ListServicesTool(BaseKubernetesTool):
    name: str = "list_k8s_services"
    description: str = (
        "List services in a Kubernetes cluster, optionally filtered by namespace."
    )
    args_schema: Type[BaseModel] = ListServicesInputSchema

    def _run(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            ret = (
                v1.list_namespaced_service(namespace, watch=False)
                if namespace
                else v1.list_service_for_all_namespaces(watch=False)
            )
            services = []
            for i in ret.items:
                ports = (
                    ",".join(
                        [f"{p.port}:{p.target_port}/{p.protocol}" for p in i.spec.ports]
                    )
                    if i.spec.ports
                    else "None"
                )
                external_ip = (
                    i.status.load_balancer.ingress[0].ip
                    if i.status.load_balancer.ingress
                    else "None"
                )
                services.append(
                    f"{i.metadata.name}\t{i.metadata.namespace}\t{i.spec.type}\t{i.spec.cluster_ip}\t{external_ip}\t{ports}"
                )
            return (
                "Service Name\tNamespace\tType\tCluster IP\tExternal IP\tPorts\n"
                + "\n".join(services)
                if services
                else "No services found."
            )
        except Exception as e:
            return f"Error listing services: {e}"

    async def _arun(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, namespace=namespace, run_manager=run_manager, **kwargs
        )


class ListDeploymentsTool(BaseKubernetesTool):
    name: str = "list_k8s_deployments"
    description: str = (
        "List deployments in a Kubernetes cluster, optionally filtered by namespace."
    )
    args_schema: Type[BaseModel] = ListDeploymentsInputSchema

    def _run(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        apps_v1 = client.AppsV1Api(self.api_client)
        try:
            ret = (
                apps_v1.list_namespaced_deployment(namespace, watch=False)
                if namespace
                else apps_v1.list_deployment_for_all_namespaces(watch=False)
            )
            deployments = []
            for i in ret.items:
                replicas = f"{i.status.ready_replicas or 0}/{i.spec.replicas}"
                age = _calculate_age(i.metadata.creation_timestamp)
                deployments.append(
                    f"{i.metadata.name}\t{i.metadata.namespace}\t{replicas}\t{age}"
                )
            return (
                "Deployment Name\tNamespace\tReplicas\tAge\n" + "\n".join(deployments)
                if deployments
                else "No deployments found."
            )
        except Exception as e:
            return f"Error listing deployments: {e}"

    async def _arun(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, namespace=namespace, run_manager=run_manager, **kwargs
        )


class ListNodesTool(BaseKubernetesTool):
    name: str = "list_k8s_nodes"
    description: str = (
        "List nodes in a Kubernetes cluster, optionally filtered by label selectors."
    )
    args_schema: Type[BaseModel] = ListNodesInputSchema

    def _run(
        self,
        label_selector: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            ret = v1.list_node(label_selector=label_selector or "", watch=False)
            nodes = []
            for i in ret.items:
                status = (
                    "Ready"
                    if any(
                        c.type == "Ready" and c.status == "True"
                        for c in i.status.conditions
                    )
                    else "NotReady"
                )
                roles = (
                    ",".join(
                        [
                            k.split("/")[-1]
                            for k in i.metadata.labels
                            if "node-role.kubernetes.io/" in k
                        ]
                    )
                    or "<none>"
                )
                age = _calculate_age(i.metadata.creation_timestamp)
                internal_ip = next(
                    (
                        addr.address
                        for addr in i.status.addresses
                        if addr.type == "InternalIP"
                    ),
                    "N/A",
                )
                nodes.append(
                    f"{i.metadata.name}\t{status}\t{roles}\t{age}\t{i.status.node_info.kubelet_version}\t{internal_ip}"
                )
            return (
                "Node Name\tStatus\tRoles\tAge\tVersion\tInternal IP\n"
                + "\n".join(nodes)
                if nodes
                else "No nodes found."
            )
        except Exception as e:
            return f"Error listing nodes: {e}"

    async def _arun(
        self,
        label_selector: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, label_selector=label_selector, run_manager=run_manager, **kwargs
        )


class GetPodLogsTool(BaseKubernetesTool):
    name: str = "get_k8s_pod_logs"
    description: str = (
        "Get logs from a Kubernetes pod, optionally from a specific container."
    )
    args_schema: Type[BaseModel] = GetPodLogsInputSchema

    def _run(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = 100,
        previous: Optional[bool] = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            logs = v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
                previous=previous,
            )
            return logs if logs else "No logs found for the specified pod."
        except Exception as e:
            return f"Error getting pod logs: {e}"

    async def _arun(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = 100,
        previous: Optional[bool] = False,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run,
            namespace=namespace,
            pod_name=pod_name,
            container=container,
            tail_lines=tail_lines,
            previous=previous,
            run_manager=run_manager,
            **kwargs,
        )


class ScaleDeploymentTool(BaseKubernetesTool):
    name: str = "scale_k8s_deployment"
    description: str = "Scale a Kubernetes deployment to a specific number of replicas."
    args_schema: Type[BaseModel] = ScaleDeploymentInputSchema

    def _run(
        self,
        namespace: str,
        deployment_name: str,
        replicas: int,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        apps_v1 = client.AppsV1Api(self.api_client)
        try:
            if replicas < 0:
                return "Error: Replica count cannot be negative."
            patch_body = {"spec": {"replicas": replicas}}
            apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name, namespace=namespace, body=patch_body
            )
            return f"Successfully scaled deployment '{deployment_name}' in namespace '{namespace}' to {replicas} replicas."
        except Exception as e:
            return f"Error scaling deployment: {e}"

    async def _arun(
        self,
        namespace: str,
        deployment_name: str,
        replicas: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run,
            namespace=namespace,
            deployment_name=deployment_name,
            replicas=replicas,
            run_manager=run_manager,
            **kwargs,
        )


class CreateNamespaceTool(BaseKubernetesTool):
    name: str = "create_k8s_namespace"
    description: str = "Create a new Kubernetes namespace with optional labels."
    args_schema: Type[BaseModel] = CreateNamespaceInputSchema

    def _run(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            namespace = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=name, labels=labels or {})
            )
            v1.create_namespace(body=namespace)
            labels_str = (
                ", ".join([f"{k}={v}" for k, v in (labels or {}).items()])
                if labels
                else "None"
            )
            return f"Successfully created namespace '{name}' with labels: {labels_str}"
        except Exception as e:
            return f"Error creating namespace: {e}"

    async def _arun(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, name=name, labels=labels, run_manager=run_manager, **kwargs
        )


class DeletePodTool(BaseKubernetesTool):
    name: str = "delete_k8s_pod"
    description: str = "Delete a Kubernetes pod with configurable grace period."
    args_schema: Type[BaseModel] = DeletePodInputSchema

    def _run(
        self,
        namespace: str,
        pod_name: str,
        grace_period: Optional[int] = 30,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            v1.delete_namespaced_pod(
                name=pod_name, namespace=namespace, grace_period_seconds=grace_period
            )
            return f"Successfully deleted pod '{pod_name}' in namespace '{namespace}' with grace period {grace_period} seconds."
        except Exception as e:
            return f"Error deleting pod: {e}"

    async def _arun(
        self,
        namespace: str,
        pod_name: str,
        grace_period: Optional[int] = 30,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run,
            namespace=namespace,
            pod_name=pod_name,
            grace_period=grace_period,
            run_manager=run_manager,
            **kwargs,
        )


class GetServiceTool(BaseKubernetesTool):
    name: str = "get_k8s_service"
    description: str = "Get detailed information about a Kubernetes service."
    args_schema: Type[BaseModel] = GetServiceInputSchema

    def _run(
        self,
        namespace: str,
        service_name: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            service = v1.read_namespaced_service(name=service_name, namespace=namespace)
            info = f"Service: {service.metadata.name}\nNamespace: {service.metadata.namespace}\nType: {service.spec.type}\nCluster IP: {service.spec.cluster_ip}\n"
            if service.spec.ports:
                info += f"Ports: {', '.join([f'{p.port}:{p.target_port}/{p.protocol}' for p in service.spec.ports])}\n"
            if service.status.load_balancer.ingress:
                info += f"External IPs: {', '.join([ing.ip or ing.hostname for ing in service.status.load_balancer.ingress])}\n"
            return info
        except Exception as e:
            return f"Error getting service details: {e}"

    async def _arun(
        self,
        namespace: str,
        service_name: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run,
            namespace=namespace,
            service_name=service_name,
            run_manager=run_manager,
            **kwargs,
        )


class ListConfigMapsTool(BaseKubernetesTool):
    name: str = "list_k8s_configmaps"
    description: str = (
        "List configmaps in a Kubernetes cluster, optionally filtered by namespace."
    )
    args_schema: Type[BaseModel] = ListConfigMapsInputSchema

    def _run(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            ret = (
                v1.list_namespaced_config_map(namespace, watch=False)
                if namespace
                else v1.list_config_map_for_all_namespaces(watch=False)
            )
            configmaps = []
            for i in ret.items:
                configmaps.append(
                    f"{i.metadata.name}\t{i.metadata.namespace}\t{len(i.data) if i.data else 0}\t{_calculate_age(i.metadata.creation_timestamp)}"
                )
            return (
                "ConfigMap Name\tNamespace\tData Keys\tAge\n" + "\n".join(configmaps)
                if configmaps
                else "No configmaps found."
            )
        except Exception as e:
            return f"Error listing configmaps: {e}"

    async def _arun(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, namespace=namespace, run_manager=run_manager, **kwargs
        )


class ListSecretsTool(BaseKubernetesTool):
    name: str = "list_k8s_secrets"
    description: str = (
        "List secrets in a Kubernetes cluster, optionally filtered by namespace."
    )
    args_schema: Type[BaseModel] = ListSecretsInputSchema

    def _run(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        v1 = client.CoreV1Api(self.api_client)
        try:
            ret = (
                v1.list_namespaced_secret(namespace, watch=False)
                if namespace
                else v1.list_secret_for_all_namespaces(watch=False)
            )
            secrets = []
            for i in ret.items:
                secrets.append(
                    f"{i.metadata.name}\t{i.metadata.namespace}\t{i.type or 'Opaque'}\t{len(i.data) if i.data else 0}\t{_calculate_age(i.metadata.creation_timestamp)}"
                )
            return (
                "Secret Name\tNamespace\tType\tData Keys\tAge\n" + "\n".join(secrets)
                if secrets
                else "No secrets found."
            )
        except Exception as e:
            return f"Error listing secrets: {e}"

    async def _arun(
        self,
        namespace: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._run, namespace=namespace, run_manager=run_manager, **kwargs
        )
