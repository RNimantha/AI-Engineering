from collections.abc import AsyncGenerator
from dataclasses import dataclass

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import McpSSEServerConfig

from tools import all_tools, tools_server

NOTES_SERVER: McpSSEServerConfig = {
    "type": "sse",
    "url": "http://127.0.0.1:8001/sse",
}


@dataclass
class AgentEvent:
    type: str
    content: str


@dataclass
class AgentReply:
    message: str
    events: list[AgentEvent]


class ClaudeAgentService:
    def __init__(self):
        self.tool_names = [tool.name for tool in all_tools]

    NOTES_TOOLS = ["create_note", "list_notes", "get_note", "delete_note"]

    DRIVE_TOOLS = [
        "search_files",
        "list_recent_files",
        "read_file_content",
        "download_file_content",
        "get_file_metadata",
        "get_file_permissions",
        "copy_file",
        "create_file",
    ]

    def _build_prompt(self, messages: list[dict[str, str]]) -> str:
        preface = (
            "You are a helpful assistant for this local agents project. "
            "Use the available tools when they help answer questions about greetings, inventory, user management, "
            "notes, or Google Drive files and Google Sheets."
        )
        transcript = "\n".join(
            f"{message['role'].capitalize()}: {message['content']}" for message in messages
        )
        return f"{preface}\n\nConversation:\n{transcript}\nAssistant:"

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[AgentEvent, None]:
        async for message in query(
            prompt=self._build_prompt(messages),
            options=ClaudeAgentOptions(
                mcp_servers={"my-tools": tools_server, "notes": NOTES_SERVER},
                allowed_tools=self.tool_names + ["WebSearch"] + self.DRIVE_TOOLS + self.NOTES_TOOLS,
                permission_mode="bypassPermissions",
                model="claude-haiku-4-5-20251001",
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        yield AgentEvent(type="assistant", content=block.text.strip())
                    elif hasattr(block, "name") and block.name:
                        yield AgentEvent(type="tool", content=block.name)
            elif isinstance(message, ResultMessage):
                yield AgentEvent(type="result", content=message.subtype)
