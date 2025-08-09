# file: tools/powershell/factory.py

import asyncio
from typing import Type, List, Literal

from pydantic import Field


from tools.base import AbstractTool,ToolInputSchema
from .runner import PowerShellRunner 

ps_runner = PowerShellRunner()


class RunTofuPlanInput(ToolInputSchema):
    directory: str = Field(description="The directory containing the OpenTofu configuration files.")

class RunTofuApplyInput(ToolInputSchema):
    directory: str = Field(description="The directory containing the OpenTofu configuration files.")
    auto_approve: bool = Field(default=True, Literal=True, description="Must be set to true for non-interactive execution.")

class RunGitStatusInput(ToolInputSchema):
    directory: str = Field(description="The path to the local Git repository.")

class PowerShellTool(AbstractTool):
    """
    A tool for executing specific, pre-approved PowerShell commands.
    This class is instantiated multiple times with different command_name
    values to create distinct, safe tools for the agent.
    """
    # The command_name determines which logical command this instance represents.
    command_name: Literal["tofu_plan", "tofu_apply", "git_status"]
    
    # We pass the shared runner instance during initialization.
    runner: PowerShellRunner

    def _build_command(self, **kwargs) -> str:
        """Helper method to safely construct the shell command."""
        command = ""
        if self.command_name == "tofu_plan":
            directory = kwargs.get("directory")
            command = f"cd {directory}; tofu plan -no-color"
        
        elif self.command_name == "tofu_apply":
            directory = kwargs.get("directory")
            if kwargs.get("auto_approve") is not True:
                # This check prevents the LLM from calling it interactively.
                raise ValueError("The 'auto_approve' flag must be set to true for this tool.")
            command = f"cd {directory}; tofu apply -auto-approve -no-color"

        elif self.command_name == "git_status":
            directory = kwargs.get("directory")
            command = f"cd {directory}; git status"
        
        else:
            # This case should not be reachable due to the Literal type hint.
            raise ValueError(f"Unknown internal command '{self.command_name}'.")
        
        return command

    def _run(self, **kwargs) -> str:
        """
        Sync execution logic that constructs and runs the command.
        This method fulfills the 'AbstractTool' contract.
        """
        try:
            command_to_run = self._build_command(**kwargs)
            result = self.runner.run_command(command_to_run)
            
            # Format a clean, predictable output for the LLM
            return (
                f"COMMAND: {command_to_run}\n"
                f"STATUS: {'Success' if result['returncode'] == 0 else 'Failure'}\n"
                f"STDOUT:\n{result['stdout']}\n"
                f"STDERR:\n{result['stderr']}"
            )
        except Exception as e:
            return f"Error during tool execution: {e}"

    async def _arun(self, **kwargs) -> str:
        """
        Async execution logic that runs the sync method in a thread pool.
        This method fulfills the 'AbstractTool' contract.
        """
        try:
            loop = asyncio.get_running_loop()
            # Use a lambda to pass keyword arguments to the blocking function
            result = await loop.run_in_executor(
                None, lambda: self._run(**kwargs)
            )
            return result
        except Exception as e:
            return f"Error during async tool execution: {e}"


def create_powershell_tools() -> List[AbstractTool]:
    """
    Creates and configures a list of distinct PowerShell tools for the agent.
    """
    # Define the configurations for each tool we want to create
    tool_configs = [
        {
            "command_name": "tofu_plan",
            "description": "Runs 'tofu plan' in a specified directory to preview infrastructure changes. Always runs in non-interactive mode.",
            "args_schema": RunTofuPlanInput
        },
        {
            "command_name": "tofu_apply",
            "description": "Runs 'tofu apply -auto-approve' to apply infrastructure changes. Requires explicit approval in the call.",
            "args_schema": RunTofuApplyInput
        },
        {
            "command_name": "git_status",
            "description": "Runs 'git status' to check the state of a local repository.",
            "args_schema": RunGitStatusInput
        }
    ]
    
    tools = []
    for config in tool_configs:
        # Each tool instance is distinct but shares the same PowerShell runner
        tool_instance = PowerShellTool(
            name=f"powershell_{config['command_name']}",
            description=config['description'],
            command_name=config['command_name'],
            args_schema=config['args_schema'],
            runner=ps_runner # Pass the shared runner
        )
        tools.append(tool_instance)
        
    return tools