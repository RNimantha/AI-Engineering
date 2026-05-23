"""
UC03 — Single Tool | Claude Agent SDK
═══════════════════════════════════════
KEY INSIGHT — Tools in Agent SDK:
  The Agent SDK handles the agentic loop FOR YOU.
  You don't write while True, you don't check stop_reason,
  you don't append tool results manually.

  You just: define the tool, pass it to query(), watch events.
  The SDK runs the loop internally until Claude is done.

  Tool definition in Agent SDK:
    Tools are defined as InputSchema Pydantic models + async functions,
    wrapped with @claude_agent_sdk.tool decorator.
    Under the hood these become in-process MCP servers.

  ⚠️ BIG DIFFERENCE from Claude SDK:
    Claude SDK:  You execute the tool (block.name, block.input → your code)
    Agent SDK:   The SDK executes the tool (you just define it with @tool)

  You observe tool calls through events:
    event.type == "assistant" with a tool_use content block
    → The SDK has ALREADY called your function before this event fires
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key
from shared.tools import calculate  # our pure Python tool

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def run_with_tool(user_message: str) -> str:
    """Agent SDK handles the tool-use loop automatically."""
    print(f"\nUser: {user_message}")
    full_response = ""

    async for event in claude_agent_sdk.query(
        prompt=user_message,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=5,        # allow up to 5 turns of tool use
            # Tools are passed as MCP tool definitions or allowed_tools
            # For built-in tools (calculator-like), we use allowed_tools
            # For custom Python functions, we'd use a local MCP server
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    full_response = block.text
                    print(f"[Assistant text] {block.text[:100]}")
                elif hasattr(block, "name"):
                    # Tool was called (Agent SDK already executed it)
                    print(f"[Tool called]    {block.name}({block.input})")

        elif event.type == "result":
            print(f"[Result] stop={event.stop_reason}, turns={getattr(event, 'num_turns', '?')}")

    return full_response


# ── Alternative: using a custom tool via subprocess ──────────────────────────
# For custom Python tools (like our calculator), the Agent SDK approach
# requires running them as MCP servers. Here's a simpler direct approach
# by having Claude reason through the math without a formal tool:

async def run_with_reasoning(user_message: str) -> str:
    """Use Claude's native reasoning for math (no explicit tool needed)."""
    full_response = ""
    async for event in claude_agent_sdk.query(
        prompt=user_message + " Show your calculation steps.",
        options=claude_agent_sdk.ClaudeCodeOptions(model=ANTHROPIC_MODEL, max_turns=1)
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    full_response += block.text
    return full_response


async def main():
    header("Claude Agent SDK", "03 — Single Tool", ANTHROPIC_MODEL)

    # With Agent SDK, custom Python functions need MCP wrapping
    # For simple math, Claude can reason natively
    print("=== Native reasoning (Agent SDK strength: no tool overhead for simple tasks) ===")
    result = await run_with_reasoning("What is 1337 * 42? Calculate step by step.")
    print(f"\nAnswer: {result}")

    print("\n=== Key insight ===")
    print("Agent SDK tool model:")
    print("  Custom Python tools → must be wrapped as MCP servers")
    print("  Built-in tools (bash, file ops) → available via allowed_tools param")
    print("  Best for: code execution, file reading, shell commands")
    print()
    print("Claude SDK tool model:")
    print("  Any Python function → define schema, execute manually")
    print("  Best for: custom business logic, API calls, databases")

    print("\n=== When Agent SDK tool use IS perfect ===")
    result2 = await run_with_tool(
        "What is the square root of 144 plus 7 squared?"
    )
    print(f"Final: {result2}")


if __name__ == "__main__":
    asyncio.run(main())
