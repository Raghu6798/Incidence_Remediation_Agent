# C:\Users\Raghu\Downloads\Incidence_response_agent\DevOps_Agent\tools\kubernetes\kubernetes_tool.py
# (Fully Refactored and Corrected)

import os
from dotenv import load_dotenv
from loguru import logger
from typing import Optional, List, Dict, Any

from tools.kubernetes.kubernetes_tool import (
    ListPodsTool,
    ListServicesTool,
    ListDeploymentsTool,
    ListNodesTool,
    GetPodLogsTool,
    ScaleDeploymentTool,
    CreateNamespaceTool,
    DeletePodTool,
    GetServiceTool,
    ListConfigMapsTool,
    ListSecretsTool,
)
from tools.base import AbstractTool

load_dotenv()


class KubernetesToolset:
    """
    Factory class to create and manage a set of Kubernetes tools.
    This is the recommended way to interact with the Kubernetes tools.
    """

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        cluster_context: Optional[str] = None,
    ):
        """
        Initializes the Kubernetes toolset.
        Args:
            kubeconfig_path (Optional[str]): Path to the kubeconfig file.
            cluster_context (Optional[str]): Kubernetes context to use.
        """
        logger.debug(f"Initializing Kubernetes toolset with context: {cluster_context}")
        self.kubeconfig_path = kubeconfig_path
        self.cluster_context = cluster_context
        self._tools = None

        # Test connection by creating a tool instance
        try:
            ListPodsTool(
                kubeconfig_path=self.kubeconfig_path, context=self.cluster_context
            )
            logger.info("Kubernetes toolset initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes toolset: {e}")
            raise

    @property
    def tools(self) -> List[AbstractTool]:
        """Get all available Kubernetes tools, instantiated with the correct context."""
        if self._tools is None:
            logger.debug("Creating Kubernetes tools list")

            tool_classes = [
                ListPodsTool,
                GetPodLogsTool,
                DeletePodTool,
                ListServicesTool,
                GetServiceTool,
                ListDeploymentsTool,
                ScaleDeploymentTool,
                ListNodesTool,
                CreateNamespaceTool,
                ListConfigMapsTool,
                ListSecretsTool,
            ]

            self._tools = [
                tool_class(
                    kubeconfig_path=self.kubeconfig_path, context=self.cluster_context
                )
                for tool_class in tool_classes
            ]

            logger.info(f"Successfully created {len(self._tools)} Kubernetes tools")
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[AbstractTool]:
        """Get a specific tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        logger.warning(f"Tool '{name}' not found in Kubernetes toolset")
        return None

    @classmethod
    def from_env(cls) -> "KubernetesToolset":
        """Create a KubernetesToolset instance using environment variables."""
        kubeconfig_path = os.environ.get("KUBECONFIG_PATH")
        cluster_context = os.environ.get("KUBERNETES_CONTEXT")
        logger.info("Creating Kubernetes toolset from environment variables")
        return cls(kubeconfig_path=kubeconfig_path, cluster_context=cluster_context)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "KubernetesToolset":
        """Create a KubernetesToolset instance from a configuration dictionary."""
        kubeconfig_path = config.get("kubeconfig_path")
        cluster_context = config.get("cluster_context")
        logger.info("Creating Kubernetes toolset from configuration")
        return cls(kubeconfig_path=kubeconfig_path, cluster_context=cluster_context)


# ============= USAGE EXAMPLE =============
def example_usage():
    """Example of how to use the Kubernetes toolset."""
    logger.info("--- Running Kubernetes toolset example ---")
    try:
        logger.info("Creating toolset from environment variables...")
        toolset = KubernetesToolset.from_env()

        tools = toolset.tools
        logger.info(f"Available tools: {[tool.name for tool in tools]}")

        pod_tool = toolset.get_tool_by_name("list_k8s_pods")
        if pod_tool:
            logger.info("Testing pod listing tool...")
            result = pod_tool.run({})
            print("--- All Pods ---")
            print(result)
            print("----------------")

        deployment_tool = toolset.get_tool_by_name("list_k8s_deployments")
        if deployment_tool:
            logger.info("Testing deployment listing tool...")
            result = deployment_tool.run({"namespace": "default"})
            print("--- Deployments in 'default' ---")
            print(result)
            print("------------------------------")

    except Exception as e:
        logger.error(f"Error in example usage: {e}")
        print(f"Error: {e}")


if __name__ == "__main__":
    # Configure logger for better console output
    import sys

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    example_usage()
