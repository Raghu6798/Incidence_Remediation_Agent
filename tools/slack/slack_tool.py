import json
from typing import Optional, Type, List
from pydantic import BaseModel, Field, EmailStr
from loguru import logger

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from tools.base import AbstractTool, ToolInputSchema


class SlackAPIClient:
    """A wrapper for Slack SDK clients to handle sync and async operations.
    
    This class provides a unified interface for interacting with the Slack API
    using both synchronous and asynchronous clients. It handles authentication
    and provides error handling for common API failures.
    
    Attributes:
        client (WebClient): Synchronous Slack Web API client
        async_client (AsyncWebClient): Asynchronous Slack Web API client
    
    Example:
        >>> slack_client = SlackAPIClient(token="xoxb-your-bot-token")
        >>> # Use slack_client.client for sync operations
        >>> # Use slack_client.async_client for async operations
    """

    def __init__(self, token: str):
        """Initialize the Slack API client with authentication token.
        
        Args:
            token (str): Slack Bot User OAuth Token (starts with 'xoxb-')
        
        Raises:
            ValueError: If token is empty or None
        
        Note:
            The token should have appropriate bot scopes for the operations
            you plan to perform (e.g., chat:write, channels:manage, users:read.email)
        """
        if not token:
            raise ValueError("Slack API token must be provided.")
        self.client = WebClient(token=token)
        self.async_client = AsyncWebClient(token=token)
        logger.info("Slack API client initialized successfully.")


# --- Input Schemas ---

class SendMessageInput(ToolInputSchema):
    """Input schema for sending messages to Slack channels.
    
    Attributes:
        channel (str): Channel identifier (name with # or ID)
        text (str): Message content to send
        thread_ts (Optional[str]): Parent message timestamp for threading
    """
    channel: str = Field(
        description="The channel name (e.g., '#general') or channel ID (e.g., 'C12345678')."
    )
    text: str = Field(description="The text of the message to send.")
    thread_ts: Optional[str] = Field(
        default=None,
        description="The 'ts' value of a parent message to reply in a thread.",
    )


class CreateChannelInput(ToolInputSchema):
    """Input schema for creating new Slack channels.
    
    Attributes:
        name (str): Channel name without # prefix
        is_private (bool): Whether channel should be private (default: False)
    """
    name: str = Field(
        description="The name of the channel to create (without the '#' prefix). e.g., 'incident-2024-api-outage'"
    )
    is_private: bool = Field(
        default=False, description="Whether the channel should be private."
    )


class InviteUsersInput(ToolInputSchema):
    """Input schema for inviting users to channels.
    
    Attributes:
        channel (str): Target channel ID
        user_ids (List[str]): List of user IDs to invite
    """
    channel: str = Field(description="The channel ID to invite users to.")
    user_ids: List[str] = Field(
        description="A list of user IDs to invite (e.g., ['U012AB3CD', 'U023EF4GH'])."
    )


class ArchiveChannelInput(ToolInputSchema):
    """Input schema for archiving channels.
    
    Attributes:
        channel (str): Channel ID to archive
    """
    channel: str = Field(description="The channel ID to archive.")


class PinMessageInput(ToolInputSchema):
    """Input schema for pinning messages.
    
    Attributes:
        channel (str): Channel ID where message exists
        timestamp (str): Message timestamp to pin
    """
    channel: str = Field(description="The channel ID where the message exists.")
    timestamp: str = Field(description="The 'ts' value of the message to pin.")


class FindUserByEmailInput(ToolInputSchema):
    """Input schema for finding users by email.
    
    Attributes:
        email (EmailStr): Email address to search for
    """
    email: EmailStr = Field(description="The email address of the user to find.")


# --- Tool Definitions ---

class SendMessageTool(AbstractTool):
    """Tool for sending messages to Slack channels with optional threading support.
    
    This tool enables the incident response agent to communicate updates, alerts,
    and status messages to relevant channels. It supports both standalone messages
    and threaded replies for organized conversations during incidents.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    Example Usage:
        During incident response:
        - Send initial incident notifications
        - Post status updates to incident channels
        - Reply to specific threads with detailed information
        - Broadcast resolution messages
    
    Returns:
        JSON string containing:
        - success (bool): Whether the operation succeeded
        - timestamp (str): Message timestamp if successful
        - channel (str): Channel ID where message was posted
        - error (str): Error details if failed
    """
    name: str = "slack_send_message"
    description: str = "Sends a message to a specified Slack channel. Can also be used to reply to a thread."
    args_schema: Type[BaseModel] = SendMessageInput
    slack_client: SlackAPIClient

    def _run(self, channel: str, text: str, thread_ts: Optional[str] = None) -> str:
        """Send a message to a Slack channel synchronously.
        
        Args:
            channel (str): Channel name (#general) or ID (C12345678)
            text (str): Message content to send
            thread_ts (Optional[str]): Parent message timestamp for threading
        
        Returns:
            str: JSON response with success status and message details
        
        Raises:
            SlackApiError: When API request fails (handled internally)
        
        Note:
            - Channel names must include # prefix or use channel ID
            - For threading, thread_ts should be the 'ts' value from parent message
            - Bot must be a member of the channel to send messages
        """
        try:
            response = self.slack_client.client.chat_postMessage(
                channel=channel, text=text, thread_ts=thread_ts
            )
            return json.dumps(
                {
                    "success": True,
                    "timestamp": response["ts"],
                    "channel": response["channel"],
                }
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(
        self, channel: str, text: str, thread_ts: Optional[str] = None
    ) -> str:
        """Send a message to a Slack channel asynchronously.
        
        Args:
            channel (str): Channel name (#general) or ID (C12345678)
            text (str): Message content to send
            thread_ts (Optional[str]): Parent message timestamp for threading
        
        Returns:
            str: JSON response with success status and message details
        
        Note:
            Async version for non-blocking operations in event-driven architectures.
        """
        try:
            response = await self.slack_client.async_client.chat_postMessage(
                channel=channel, text=text, thread_ts=thread_ts
            )
            return json.dumps(
                {
                    "success": True,
                    "timestamp": response["ts"],
                    "channel": response["channel"],
                }
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})


class CreateChannelTool(AbstractTool):
    """Tool for creating new Slack channels for incident management.
    
    This tool is essential for establishing dedicated 'war rooms' during incidents,
    providing isolated spaces for incident-specific communication and coordination.
    Supports both public and private channel creation based on incident sensitivity.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    Channel Naming Conventions:
        - incident-YYYY-MM-DD-brief-description
        - incident-2024-api-outage
        - incident-database-performance
    
    Example Usage:
        - Create dedicated incident channels automatically
        - Establish private channels for sensitive security incidents
        - Set up temporary project channels for incident response coordination
    
    Returns:
        JSON string containing:
        - success (bool): Whether the channel was created
        - channel_id (str): Unique identifier of the new channel
        - name (str): Actual name of the created channel
        - error (str): Error details if creation failed
    """
    name: str = "slack_create_channel"
    description: str = "Creates a new public or private Slack channel. Essential for creating incident 'war rooms'."
    args_schema: Type[BaseModel] = CreateChannelInput
    slack_client: SlackAPIClient

    def _run(self, name: str, is_private: bool = False) -> str:
        """Create a new Slack channel synchronously.
        
        Args:
            name (str): Channel name without # prefix (lowercase, hyphens allowed)
            is_private (bool): If True, creates private channel; False for public
        
        Returns:
            str: JSON response with channel creation details
        
        Channel Name Requirements:
            - Must be lowercase
            - Can contain hyphens and underscores
            - Cannot contain spaces or special characters
            - Maximum 80 characters
            - Must be unique within the workspace
        
        Permissions Required:
            - channels:manage (for public channels)
            - groups:write (for private channels)
        
        Note:
            The bot automatically becomes a member of channels it creates.
        """
        try:
            response = self.slack_client.client.conversations_create(
                name=name, is_private=is_private
            )
            channel_info = response["channel"]
            return json.dumps(
                {
                    "success": True,
                    "channel_id": channel_info["id"],
                    "name": channel_info["name"],
                }
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(self, name: str, is_private: bool = False) -> str:
        """Create a new Slack channel asynchronously.
        
        Args:
            name (str): Channel name without # prefix
            is_private (bool): Whether to create a private channel
        
        Returns:
            str: JSON response with channel creation details
        
        Note:
            Async version for non-blocking channel creation in automated workflows.
        """
        try:
            response = await self.slack_client.async_client.conversations_create(
                name=name, is_private=is_private
            )
            channel_info = response["channel"]
            return json.dumps(
                {
                    "success": True,
                    "channel_id": channel_info["id"],
                    "name": channel_info["name"],
                }
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})


class InviteUsersTool(AbstractTool):
    """Tool for inviting users to Slack channels during incident response.
    
    This tool enables the automatic assembly of incident response teams by
    inviting relevant personnel to incident channels based on their roles,
    expertise, or escalation policies. Supports bulk invitations for efficiency.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    Common Use Cases:
        - Invite on-call engineers to incident channels
        - Add subject matter experts based on affected services
        - Include management in high-severity incidents
        - Bring in additional responders during escalation
    
    Permissions Required:
        - channels:manage (for public channels)
        - groups:write (for private channels)
    
    Returns:
        JSON string containing:
        - success (bool): Whether invitations were sent successfully
        - channel (str): Channel ID where users were invited
        - error (str): Error details if invitation failed
    
    Note:
        Users must be workspace members to be invited to channels.
        Failed invitations for individual users don't fail the entire operation.
    """
    name: str = "slack_invite_users"
    description: str = "Invites one or more users to a Slack channel. Used to bring responders into an incident channel."
    args_schema: Type[BaseModel] = InviteUsersInput
    slack_client: SlackAPIClient

    def _run(self, channel: str, user_ids: List[str]) -> str:
        """Invite multiple users to a channel synchronously.
        
        Args:
            channel (str): Target channel ID (e.g., 'C12345678')
            user_ids (List[str]): List of user IDs to invite (e.g., ['U123', 'U456'])
        
        Returns:
            str: JSON response with invitation results
        
        Behavior:
            - Users already in the channel are silently ignored
            - Invalid user IDs are reported in the error response
            - Partial failures are possible (some users invited, others failed)
        
        Rate Limits:
            - Slack API allows up to 1000 users per invitation call
            - Consider batching for very large user lists
        
        Note:
            User IDs can be obtained using FindUserByEmailTool or other user lookup methods.
        """
        try:
            response = self.slack_client.client.conversations_invite(
                channel=channel, users=",".join(user_ids)
            )
            return json.dumps({"success": True, "channel": response["channel"]["id"]})
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(self, channel: str, user_ids: List[str]) -> str:
        """Invite multiple users to a channel asynchronously.
        
        Args:
            channel (str): Target channel ID
            user_ids (List[str]): List of user IDs to invite
        
        Returns:
            str: JSON response with invitation results
        
        Note:
            Async version for non-blocking user invitations in automated workflows.
        """
        try:
            response = await self.slack_client.async_client.conversations_invite(
                channel=channel, users=",".join(user_ids)
            )
            return json.dumps({"success": True, "channel": response["channel"]["id"]})
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})


class ArchiveChannelTool(AbstractTool):
    """Tool for archiving Slack channels after incident resolution.
    
    This tool provides cleanup capabilities for incident response workflows,
    archiving channels that are no longer active while preserving their
    message history for future reference and post-incident analysis.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    When to Archive:
        - Incident has been fully resolved and documented
        - Channel is no longer needed for active discussion
        - Part of incident closure procedures
        - Workspace cleanup and organization
    
    Effects of Archiving:
        - Channel becomes read-only
        - No new messages can be posted
        - Channel remains searchable
        - Message history is preserved
        - Channel can be unarchived if needed
    
    Permissions Required:
        - channels:manage (for public channels)
        - groups:write (for private channels)
    
    Returns:
        JSON string containing:
        - success (bool): Whether archival was successful
        - message (str): Confirmation message
        - error (str): Error details if archival failed
    """
    name: str = "slack_archive_channel"
    description: str = "Archives a Slack channel. Use this to clean up incident channels after they are resolved."
    args_schema: Type[BaseModel] = ArchiveChannelInput
    slack_client: SlackAPIClient

    def _run(self, channel: str) -> str:
        """Archive a Slack channel synchronously.
        
        Args:
            channel (str): Channel ID to archive (e.g., 'C12345678')
        
        Returns:
            str: JSON response with archival confirmation
        
        Preconditions:
            - Channel must exist and be active (not already archived)
            - Bot must have appropriate permissions in the channel
            - Cannot archive general or other restricted channels
        
        Best Practices:
            - Verify incident is fully resolved before archiving
            - Consider posting a final summary message before archiving
            - Document the channel in incident records for future reference
        
        Note:
            Archived channels can be unarchived by workspace admins if needed.
        """
        try:
            self.slack_client.client.conversations_archive(channel=channel)
            return json.dumps(
                {"success": True, "message": f"Channel {channel} archived."}
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(self, channel: str) -> str:
        """Archive a Slack channel asynchronously.
        
        Args:
            channel (str): Channel ID to archive
        
        Returns:
            str: JSON response with archival confirmation
        
        Note:
            Async version for non-blocking channel archival in cleanup workflows.
        """
        try:
            await self.slack_client.async_client.conversations_archive(channel=channel)
            return json.dumps(
                {"success": True, "message": f"Channel {channel} archived."}
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})


class PinMessageTool(AbstractTool):
    """Tool for pinning important messages to Slack channels.
    
    This tool helps maintain organization during incident response by pinning
    critical information such as incident summaries, key findings, action items,
    and resolution updates for easy reference by all channel members.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    Common Pinned Content:
        - Initial incident declaration and severity
        - Current status and impact assessment
        - Key investigation findings
        - Action items and assignments
        - Resolution summaries and next steps
        - Important contact information
    
    Pin Limitations:
        - Maximum 100 pinned messages per channel
        - Only channel members can view pinned messages
        - Pins are ordered by creation time (newest first)
    
    Permissions Required:
        - pins:write scope
        - Bot must be a member of the target channel
    
    Returns:
        JSON string containing:
        - success (bool): Whether message was pinned successfully
        - message (str): Confirmation message
        - error (str): Error details if pinning failed
    """
    name: str = "slack_pin_message"
    description: str = "Pins a message to a channel. Useful for pinning incident summaries or key findings."
    args_schema: Type[BaseModel] = PinMessageInput
    slack_client: SlackAPIClient

    def _run(self, channel: str, timestamp: str) -> str:
        """Pin a message to a Slack channel synchronously.
        
        Args:
            channel (str): Channel ID where the message exists (e.g., 'C12345678')
            timestamp (str): Message timestamp ('ts' value from message object)
        
        Returns:
            str: JSON response with pinning confirmation
        
        Finding Message Timestamps:
            - Use the 'ts' field from chat.postMessage responses
            - Available in message objects from conversations.history
            - Displayed in Slack UI when copying message links
        
        Best Practices:
            - Pin messages that will be referenced frequently
            - Update pins as incident status changes
            - Consider unpinning outdated information
            - Use clear, descriptive message content for pinned items
        
        Note:
            Message must exist in the specified channel before it can be pinned.
        """
        try:
            self.slack_client.client.pins_add(channel=channel, timestamp=timestamp)
            return json.dumps(
                {"success": True, "message": "Message pinned successfully."}
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(self, channel: str, timestamp: str) -> str:
        """Pin a message to a Slack channel asynchronously.
        
        Args:
            channel (str): Channel ID where the message exists
            timestamp (str): Message timestamp to pin
        
        Returns:
            str: JSON response with pinning confirmation
        
        Note:
            Async version for non-blocking message pinning in automated workflows.
        """
        try:
            await self.slack_client.async_client.pins_add(
                channel=channel, timestamp=timestamp
            )
            return json.dumps(
                {"success": True, "message": "Message pinned successfully."}
            )
        except SlackApiError as e:
            return json.dumps({"success": False, "error": e.response["error"]})


class FindUserByEmailTool(AbstractTool):
    """Tool for finding Slack users by their email addresses.
    
    This tool enables user discovery for incident response automation by
    resolving email addresses to Slack user IDs and profile information.
    Essential for building responder teams and escalation workflows.
    
    Attributes:
        name (str): Tool identifier for the agent framework
        description (str): Human-readable description of tool functionality
        args_schema (Type[BaseModel]): Pydantic schema for input validation
        slack_client (SlackAPIClient): Authenticated Slack API client
    
    Use Cases:
        - Resolve on-call engineer emails to user IDs for channel invitations
        - Look up team members for incident response assignment
        - Validate user existence before attempting operations
        - Build user directories for automated escalation
    
    Returned User Information:
        - id: Slack user ID (required for most API operations)
        - name: Username/handle
        - real_name: Display name
        - is_bot: Whether the user is a bot account
        - tz: User's timezone
    
    Privacy Considerations:
        - Only works with workspace members
        - Respects user privacy settings
        - Limited to basic profile information
    
    Permissions Required:
        - users:read scope
        - users:read.email scope
    
    Returns:
        JSON string containing:
        - success (bool): Whether user was found
        - user (dict): User profile information if found
        - error (str): Error details if lookup failed
    """
    name: str = "slack_find_user_by_email"
    description: str = "Finds a Slack user's ID and profile information using their email address."
    args_schema: Type[BaseModel] = FindUserByEmailInput
    slack_client: SlackAPIClient

    def _run(self, email: str) -> str:
        """Find a Slack user by email address synchronously.
        
        Args:
            email (str): Email address to search for (must be valid email format)
        
        Returns:
            str: JSON response with user information or error details
        
        Response Format:
            Success: {"success": true, "user": {...}}
            Not Found: {"success": false, "error": "User not found with that email."}
            Other Error: {"success": false, "error": "specific_error_code"}
        
        Common Error Codes:
            - users_not_found: No user with that email in workspace
            - invalid_email: Email format is invalid
            - missing_scope: Insufficient permissions
        
        Note:
            Email addresses are case-insensitive for lookup purposes.
        """
        try:
            response = self.slack_client.client.users_lookupByEmail(email=email)
            user_info = response["user"]
            filtered_info = {
                "id": user_info.get("id"),
                "name": user_info.get("name"),
                "real_name": user_info.get("real_name"),
                "is_bot": user_info.get("is_bot"),
                "tz": user_info.get("tz"),
            }
            return json.dumps({"success": True, "user": filtered_info})
        except SlackApiError as e:
            if e.response["error"] == "users_not_found":
                return json.dumps({"success": False, "error": "User not found with that email."})
            return json.dumps({"success": False, "error": e.response["error"]})

    async def _arun(self, email: str) -> str:
        """Find a Slack user by email address asynchronously.
        
        Args:
            email (str): Email address to search for
        
        Returns:
            str: JSON response with user information or error details
        
        Note:
            Async version for non-blocking user lookup in automated workflows.
            Useful when resolving multiple email addresses concurrently.
        """
        try:
            response = await self.slack_client.async_client.users_lookupByEmail(email=email)
            user_info = response["user"]
            filtered_info = {
                "id": user_info.get("id"),
                "name": user_info.get("name"),
                "real_name": user_info.get("real_name"),
                "is_bot": user_info.get("is_bot"),
                "tz": user_info.get("tz"),
            }
            return json.dumps({"success": True, "user": filtered_info})
        except SlackApiError as e:
            if e.response["error"] == "users_not_found":
                return json.dumps({"success": False, "error": "User not found with that email."})
            return json.dumps({"success": False, "error": e.response["error"]})