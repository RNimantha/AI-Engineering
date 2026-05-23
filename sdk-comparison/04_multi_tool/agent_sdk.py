"""
UC04 — Multi-Tool | Claude Agent SDK
════════════════════════════════════════
KEY INSIGHT — Agent SDK with multiple tools:
  The Agent SDK is especially powerful here because Claude Code natively
  understands how to orchestrate multiple tools. You can allow specific
  built-in tools via allowed_tools, and Claude manages the orchestration.

  Built-in tools available in Agent SDK:
    "Bash"         → run shell commands (VERY powerful)
    "Read"         → read files
    "Write"        → write files
    "Edit"         → edit files
    "WebSearch"    → search the web
    "WebFetch"     → fetch a URL

  For custom Python tools, you'd create a local MCP server.
  But for this comparison, we'll show how to use the built-in
  multi-step reasoning with allowed built-in tools.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def run_agent(prompt: str, show_events: bool = True) -> str:
    """Run with multiple allowed tools, observing all events."""
    print(f"\nUser: {prompt}")
    final_text = ""
    tool_calls_seen = []

    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=10,
            # Agent SDK's built-in tool allowlist
            # For this demo, we allow bash for calculations
            allowed_tools=["Bash"],
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    final_text = block.text
                    if show_events:
                        print(f"[Assistant] {block.text[:100]}")
                elif hasattr(block, "name"):
                    tool_calls_seen.append(block.name)
                    if show_events:
                        print(f"[Tool call] {block.name}")

        elif event.type == "result":
            if show_events:
                print(f"[Done] turns={getattr(event,'num_turns','?')}, "
                      f"stop={event.stop_reason}")

    if show_events and tool_calls_seen:
        print(f"[Tools used]: {tool_calls_seen}")

    return final_text


async def multi_step_reasoning(prompt: str) -> str:
    """
    Agent SDK shines here: Claude can use Bash to run Python calculations,
    making it a genuine multi-tool agent without manual tool dispatch.
    """
    final_text = ""
    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=8,
            allowed_tools=["Bash"],
            system_prompt=(
                "You have access to Bash. Use Python one-liners for calculations. "
                "Be concise in your final answer."
            )
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    final_text = block.text
    return final_text


async def main():
    header("Claude Agent SDK", "04 — Multi-Tool", ANTHROPIC_MODEL)

    print("=== Multi-step reasoning with Bash tool ===")
    result = await multi_step_reasoning(
        "Calculate: (1) What is 1337 * 42? "
        "(2) What is $10000 at 7% for 20 years? Formula: 10000 * (1.07**20) "
        "Give both answers."
    )
    print(f"\nResult: {result}")

    print("\n=== Observing all events ===")
    await run_agent(
        "Use Python to calculate the compound interest on $5000 at 5% for 10 years.",
        show_events=True
    )

    print("\n── AGENT SDK MULTI-TOOL KEY POINTS ──")
    print("Built-in tools (Bash, Read, Write, WebSearch) = no MCP setup needed")
    print("Custom Python tools = wrap as local MCP server")
    print("Agent SDK manages ALL tool orchestration, history, retries")
    print("You just observe events — no loop management needed")


if __name__ == "__main__":
    asyncio.run(main())
