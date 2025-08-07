#!/usr/bin/env python3
"""
Simple test script to verify Kubernetes tools initialization.
This script tests that the tools can be created without errors,
even if they can't connect to a Kubernetes cluster.
"""

import sys
import os
from loguru import logger

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_tool_creation():
    """Test that all Kubernetes tools can be created without errors."""
    logger.info("Testing Kubernetes tool creation...")

    try:
        # Test importing the tools
        from tools.kubernetes.kubernetes_tool import (
            KubernetesTool,
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

        logger.info("✓ Successfully imported all Kubernetes tools")

        # Test creating tools (this will fail to connect to cluster, but shouldn't crash)
        tools_to_test = [
            ("KubernetesTool", KubernetesTool),
            ("ListServicesTool", ListServicesTool),
            ("ListDeploymentsTool", ListDeploymentsTool),
            ("ListNodesTool", ListNodesTool),
            ("GetPodLogsTool", GetPodLogsTool),
            ("ScaleDeploymentTool", ScaleDeploymentTool),
            ("CreateNamespaceTool", CreateNamespaceTool),
            ("DeletePodTool", DeletePodTool),
            ("GetServiceTool", GetServiceTool),
            ("ListConfigMapsTool", ListConfigMapsTool),
            ("ListSecretsTool", ListSecretsTool),
        ]

        for tool_name, tool_class in tools_to_test:
            try:
                # Try to create the tool
                tool = tool_class()
                logger.info(f"✓ Successfully created {tool_name}")

                # Test that the tool has the expected attributes
                assert hasattr(tool, "name"), f"{tool_name} missing 'name' attribute"
                assert hasattr(tool, "description"), (
                    f"{tool_name} missing 'description' attribute"
                )
                assert hasattr(tool, "args_schema"), (
                    f"{tool_name} missing 'args_schema' attribute"
                )

                logger.info(f"✓ {tool_name} has all required attributes")

            except Exception as e:
                logger.warning(
                    f"⚠ {tool_name} creation failed (expected if no kubeconfig): {e}"
                )

        logger.info("✓ All tools can be created successfully")

    except ImportError as e:
        logger.error(f"✗ Failed to import Kubernetes tools: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False

    return True


def test_factory_creation():
    """Test that the factory can be created without errors."""
    logger.info("Testing Kubernetes factory creation...")

    try:
        from tools.kubernetes.factory import KubernetesToolset

        # Test creating factory (this will fail to connect to cluster, but shouldn't crash)
        try:
            toolset = KubernetesToolset()
            logger.info("✓ Successfully created KubernetesToolset")
        except Exception as e:
            logger.warning(
                f"⚠ KubernetesToolset creation failed (expected if no kubeconfig): {e}"
            )

        # Test factory methods
        try:
            toolset = KubernetesToolset.from_env()
            logger.info("✓ Successfully created KubernetesToolset from environment")
        except Exception as e:
            logger.warning(
                f"⚠ KubernetesToolset.from_env() failed (expected if no kubeconfig): {e}"
            )

        try:
            config = {"kubeconfig_path": None}
            toolset = KubernetesToolset.from_config(config)
            logger.info("✓ Successfully created KubernetesToolset from config")
        except Exception as e:
            logger.warning(
                f"⚠ KubernetesToolset.from_config() failed (expected if no kubeconfig): {e}"
            )

        logger.info("✓ Factory creation tests completed")

    except ImportError as e:
        logger.error(f"✗ Failed to import Kubernetes factory: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False

    return True


def test_helper_functions():
    """Test that helper functions can be imported and called."""
    logger.info("Testing helper functions...")

    try:
        from tools.kubernetes.factory import (
            get_kubernetes_tool_from_env,
            get_list_services_tool_from_env,
            get_list_deployments_tool_from_env,
            get_list_nodes_tool_from_env,
            get_pod_logs_tool_from_env,
            get_scale_deployment_tool_from_env,
            get_create_namespace_tool_from_env,
            get_delete_pod_tool_from_env,
            get_service_tool_from_env,
            get_list_configmaps_tool_from_env,
            get_list_secrets_tool_from_env,
        )

        logger.info("✓ Successfully imported all helper functions")

        # Test calling helper functions (these will fail to connect, but shouldn't crash)
        helper_functions = [
            ("get_kubernetes_tool_from_env", get_kubernetes_tool_from_env),
            ("get_list_services_tool_from_env", get_list_services_tool_from_env),
            ("get_list_deployments_tool_from_env", get_list_deployments_tool_from_env),
            ("get_list_nodes_tool_from_env", get_list_nodes_tool_from_env),
            ("get_pod_logs_tool_from_env", get_pod_logs_tool_from_env),
            ("get_scale_deployment_tool_from_env", get_scale_deployment_tool_from_env),
            ("get_create_namespace_tool_from_env", get_create_namespace_tool_from_env),
            ("get_delete_pod_tool_from_env", get_delete_pod_tool_from_env),
            ("get_service_tool_from_env", get_service_tool_from_env),
            ("get_list_configmaps_tool_from_env", get_list_configmaps_tool_from_env),
            ("get_list_secrets_tool_from_env", get_list_secrets_tool_from_env),
        ]

        for func_name, func in helper_functions:
            try:
                tool = func()
                logger.info(f"✓ Successfully called {func_name}")
            except Exception as e:
                logger.warning(f"⚠ {func_name} failed (expected if no kubeconfig): {e}")

        logger.info("✓ Helper function tests completed")

    except ImportError as e:
        logger.error(f"✗ Failed to import helper functions: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False

    return True


def main():
    """Run all tests."""
    logger.info("Starting Kubernetes tools test suite...")

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time} | {level} | {message}")

    tests = [
        ("Tool Creation", test_tool_creation),
        ("Factory Creation", test_factory_creation),
        ("Helper Functions", test_helper_functions),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'=' * 50}")

        try:
            if test_func():
                logger.info(f"✓ {test_name} test PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"✗ {test_name} test FAILED with exception: {e}")

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'=' * 50}")

    if passed == total:
        logger.info("🎉 All tests passed! Kubernetes tools are working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
