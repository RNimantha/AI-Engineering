"""
UC07 — Memory | Claude Agent SDK
══════════════════════════════════
KEY INSIGHT — Agent SDK Session-Based Memory:
  The Agent SDK has BUILT-IN session management.
  A session_id lets you resume a previous conversation automatically.
  The SDK maintains the transcript server-side (or via SessionStore).

  resume=True  → continue an existing session
  resume=False → start a new session (default)

  This is fundamentally different from manually maintaining messages[]:
    Manual memory: YOU store messages, YOU pass them on every call
    Agent SDK:     SDK stores the session, you just pass the session_id

  Use case: long-running agents that span multiple function calls
  or even multiple process restarts.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def get_last_assistant_text(events) -> str:
    """Helper: collect text from all assistant events."""
    text = ""
    async for event in events:
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    text = block.text
    return text


async def demo_session_memory():
    """
    Demonstrate session-based memory: each query continues the previous conversation.
    """
    session_id = None   # Will be set after first query

    # Turn 1 — start a new session
    print("Turn 1 (new session):")
    text1 = ""
    async for event in claude_agent_sdk.query(
        prompt="My name is Rashmika and I love building AI agents.",
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=1,
        )
    ):
        if event.type == "system":
            session_id = getattr(event, "session_id", None)
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    text1 = block.text
    print(f"  Response: {text1}")
    print(f"  Session ID: {session_id}")

    if not session_id:
        print("  (Session ID not available — falling back to manual turns)")
        await demo_manual_memory()
        return

    # Turn 2 — resume session
    print("\nTurn 2 (resuming session):")
    text2 = ""
    async for event in claude_agent_sdk.query(
        prompt="What is my name?",
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=1,
        ),
        resume=session_id,   # ← Resume the session
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    text2 = block.text
    print(f"  Response: {text2}")

    # Turn 3 — resume again
    print("\nTurn 3 (resuming session):")
    text3 = ""
    async for event in claude_agent_sdk.query(
        prompt="What hobby did I mention?",
        options=claude_agent_sdk.ClaudeCodeOptions(model=ANTHROPIC_MODEL, max_turns=1),
        resume=session_id,
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    text3 = block.text
    print(f"  Response: {text3}")


async def demo_manual_memory():
    """Fallback: Agent SDK with explicit conversation in prompt."""
    history = []

    async def turn(user_msg: str) -> str:
        history.append(f"Human: {user_msg}")
        context = "\n".join(history[-6:])  # last 3 exchanges
        full_prompt = f"Previous conversation:\n{context}\n\nCurrent message: {user_msg}"
        text = ""
        async for event in claude_agent_sdk.query(
            prompt=full_prompt,
            options=claude_agent_sdk.ClaudeCodeOptions(
                model=ANTHROPIC_MODEL, max_turns=1,
                system_prompt="You are a helpful assistant. Remember context from the conversation."
            )
        ):
            if event.type == "assistant":
                for block in event.message.content:
                    if hasattr(block, "text"):
                        text = block.text
        history.append(f"Assistant: {text}")
        return text

    print("T1:", await turn("My name is Rashmika and I love building AI agents."))
    print("T2:", await turn("What is my name?"))
    print("T3:", await turn("What hobby did I mention?"))


async def main():
    header("Claude Agent SDK", "07 — Memory / Multi-Turn", ANTHROPIC_MODEL)
    await demo_session_memory()

    print("\n── AGENT SDK MEMORY ADVANTAGE ──")
    print("session_id + resume=True: no manual messages[] management")
    print("Transcript stored by the SDK automatically")
    print("Can resume a session across multiple Python processes/restarts")
    print()
    print("vs Claude SDK: you own the messages list (more control, more code)")


if __name__ == "__main__":
    asyncio.run(main())
