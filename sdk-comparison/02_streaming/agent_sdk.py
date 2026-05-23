"""
UC02 — Streaming | Claude Agent SDK
══════════════════════════════════════
KEY INSIGHT — Agent SDK streaming:
  The Agent SDK is INHERENTLY streaming — query() is always an async generator.
  There's no "non-streaming" mode. Every call yields a sequence of typed events.

  Event types you'll see:
    system        → session metadata (session_id, model, tools available)
    assistant     → Claude's response (complete turn, not token-by-token)
    user          → echoed user input
    result        → final stats (cost, duration, turns used)

  ⚠️ IMPORTANT DIFFERENCE from Claude SDK streaming:
    Claude SDK .text_stream  → yields individual TEXT TOKENS (character by character)
    Agent SDK async for loop → yields complete TURN OBJECTS (not token-level)

  The Agent SDK doesn't expose token-level streaming — it exposes
  TURN-level streaming. You get events when Claude finishes a turn,
  not for every token within the turn.

  This is a deliberate design choice: the Agent SDK is optimised for
  observing WHAT the agent does (which tools it calls, what it decides)
  rather than watching words appear on screen.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def stream_events(prompt: str):
    """
    Demonstrate every event type the Agent SDK emits.
    This is the core pattern you use in ALL Agent SDK code.
    """
    print("─── Streaming Agent SDK events ───")

    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=1,
        )
    ):
        event_type = event.type

        if event_type == "system":
            print(f"[SYSTEM EVENT] Session started")

        elif event_type == "assistant":
            # Complete assistant turn — iterate content blocks
            print(f"[ASSISTANT EVENT] Content blocks: {len(event.message.content)}")
            for block in event.message.content:
                if hasattr(block, "text"):
                    print(f"  Text: {block.text}")
                elif hasattr(block, "name"):
                    # Tool use block
                    print(f"  Tool call: {block.name}({block.input})")

        elif event_type == "user":
            print(f"[USER EVENT] (echoed input)")

        elif event_type == "result":
            # Final event — has aggregate stats
            print(f"\n[RESULT EVENT]")
            print(f"  Stop reason:   {event.stop_reason}")
            if hasattr(event, 'total_cost_usd'):
                print(f"  Cost (USD):    ${event.total_cost_usd:.6f}")
            if hasattr(event, 'duration_ms'):
                print(f"  Duration (ms): {event.duration_ms}")
            if hasattr(event, 'num_turns'):
                print(f"  Turns used:    {event.num_turns}")


async def simple_stream(prompt: str) -> str:
    """Extract just the text response (ignoring event structure)."""
    text = ""
    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(model=ANTHROPIC_MODEL, max_turns=1)
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    text += block.text
    return text


async def main():
    header("Claude Agent SDK", "02 — Streaming", ANTHROPIC_MODEL)

    print("Prompt: Write a 3-sentence story about a robot learning to paint.\n")
    await stream_events("Write a 3-sentence story about a robot learning to paint.")

    print("\n── Simple text extraction ──")
    result = await simple_stream("What are 3 key principles of clean code? One line each.")
    print(result)

    print("\n── KEY TAKEAWAY ──")
    print("Agent SDK: turn-level events (great for observability)")
    print("Claude SDK: token-level streaming (great for chat UIs)")


if __name__ == "__main__":
    asyncio.run(main())
