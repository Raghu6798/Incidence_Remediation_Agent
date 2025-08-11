import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
from typing import Optional, List

from tools.base import AbstractTool
from tools.slack.slack_tool import (
    SlackAPIClient,
    SendMessageTool,
    CreateChannelTool,
    InviteUsersTool,
    ArchiveChannelTool,
    PinMessageTool,
    FindUserByEmailTool
)

load_dotenv()


class SlackToolsetFactory:
    """Factory class to create and manage all Slack tools for incident response."""

    def __init__(self, slack_bot_token: str):
        logger.debug("Initializing Slack toolset")
        self.client = SlackAPIClient(token=slack_bot_token)
        self._tools = None

    @property
    def tools(self) -> List[AbstractTool]:
        """Lazy-loads and returns a list of all available Slack tools."""
        if self._tools is None:
            logger.debug("Creating Slack tools list")
            self._tools = [
                SendMessageTool(slack_client=self.client),
                CreateChannelTool(slack_client=self.client),
                InviteUsersTool(slack_client=self.client),
                ArchiveChannelTool(slack_client=self.client),
                PinMessageTool(slack_client=self.client),
                FindUserByEmailTool(slack_client=self.client)
            ]
            logger.info(f"Successfully created {len(self._tools)} Slack tools.")
        return self._tools

    def get_tool_by_name(self, name: str) -> Optional[AbstractTool]:
        """Retrieves a specific tool instance by its name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None


# ============= USAGE EXAMPLE =============
async def example_usage():
    """Example of how to use the Slack toolset for an incident response flow."""
    logger.info("--- Running Slack Toolset Example ---")
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN environment variable not set. Aborting.")
        return

    user_to_invite = os.getenv("SLACK_TEST_USER_ID")

    factory = SlackToolsetFactory(slack_bot_token=slack_token)
    logger.info(f"Available tools: {[tool.name for tool in factory.tools]}")

    create_channel_tool = factory.get_tool_by_name("slack_create_channel")
    send_message_tool = factory.get_tool_by_name("slack_send_message")
    invite_users_tool = factory.get_tool_by_name("slack_invite_users")
    pin_message_tool = factory.get_tool_by_name("slack_pin_message")
    archive_channel_tool = factory.get_tool_by_name("slack_archive_channel")

    channel_id = None
    try:
        # 1. Create a new incident channel
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        channel_name = f"incident-test-{timestamp}"
        logger.info(f"Attempting to create channel: {channel_name}")
        # CORRECTED: Pass inputs as a single dictionary
        response_str = await create_channel_tool.ainvoke({"name": channel_name})
        response = json.loads(response_str)
        if not response.get("success"):
            raise Exception(
                f"Failed to create channel: {response.get('error', 'Unknown error')}"
            )

        channel_id = response["channel_id"]
        logger.success(f"Channel created with ID: {channel_id}")

        # 2. Post the initial alert message
        alert_text = f":rotating_light: **Incident Declared** :rotating_light:\n\n*Issue:* High latency detected on API Gateway.\n*Action:* This channel has been created to coordinate the response."
        logger.info("Sending initial alert message...")
        # CORRECTED: Pass inputs as a single dictionary
        msg_response_str = await send_message_tool.ainvoke(
            {"channel": channel_id, "text": alert_text}
        )
        msg_response = json.loads(msg_response_str)
        if not msg_response.get("success"):
            raise Exception(
                f"Failed to send message: {msg_response.get('error', 'Unknown error')}"
            )

        message_ts = msg_response["timestamp"]
        logger.success(f"Message sent. Timestamp: {message_ts}")

        # 3. Invite a user (if specified)
        if user_to_invite:
            logger.info(f"Inviting user {user_to_invite} to channel {channel_id}...")
            # CORRECTED: Pass inputs as a single dictionary
            await invite_users_tool.ainvoke(
                {"channel": channel_id, "user_ids": [user_to_invite]}
            )
            logger.success("Invite sent.")
        else:
            logger.warning("SLACK_TEST_USER_ID not set. Skipping user invite.")

        # 4. Pin the initial alert
        logger.info("Pinning the alert message...")
        # CORRECTED: Pass inputs as a single dictionary
        await pin_message_tool.ainvoke({"channel": channel_id, "timestamp": message_ts})
        logger.success("Message pinned.")

        # Simulate work being done
        await asyncio.sleep(5)
        # CORRECTED: Pass inputs as a single dictionary
        await send_message_tool.ainvoke(
            {
                "channel": channel_id,
                "text": "*Update:* Root cause identified. Rolling back deployment via Jenkins.",
            }
        )
        await asyncio.sleep(5)
        # CORRECTED: Pass inputs as a single dictionary
        await send_message_tool.ainvoke(
            {
                "channel": channel_id,
                "text": "*Update:* Rollback complete. Latency has returned to normal levels. Monitoring.",
            }
        )
        await asyncio.sleep(5)
        # CORRECTED: Pass inputs as a single dictionary
        await send_message_tool.ainvoke(
            {
                "channel": channel_id,
                "text": ":white_check_mark: **Incident Resolved** :white_check_mark:\n\nArchiving this channel in 10 seconds.",
            }
        )
        await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"An error occurred during the incident flow: {e}")
    finally:
        # 5. Archive the channel after the incident is resolved
        if channel_id and archive_channel_tool:
            logger.info(f"Archiving channel {channel_id}...")
            # CORRECTED: Pass inputs as a single dictionary
            await archive_channel_tool.ainvoke({"channel": channel_id})
            logger.success("Channel archived.")


if __name__ == "__main__":
    asyncio.run(example_usage())
