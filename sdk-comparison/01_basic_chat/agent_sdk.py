"""
UC01 — Basic Chat | Claude Agent SDK (claude-agent-sdk)
═══════════════════════════════════════════════════════
KEY INSIGHT — Claude Agent SDK:
  The Agent SDK was built for AGENTIC workflows (Claude Code-style tasks:
  reading files, running shell commands, writing code). Using it for basic
  chat is like using a Ferrari for grocery shopping — it works, but you'll
  see why it's overkill here.

  The fundamental difference:
    Claude SDK   → client.messages.create()  → synchronous, returns Message
    Agent SDK    → claude_agent_sdk.query()  → ASYNC GENERATOR, yields events

  You don't get a single response back. You get a stream of typed events:
    - "system"    : metadata about the session
    - "assistant" : Claude's response (may include tool calls)
    - "result"    : final result with cost/duration stats
    - "user"      : echoed user turns (for context)

  This event-stream design is perfect when you want to observe an agent
  thinking step-by-step, but verbose for a single Q&A.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.utils import load_env, header, require_key, model_use, total_usage
from shared.utils import load_env, header, require_key 
load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))
import claude_agent_sdk
ANTHROPIC_MODEL = model_use("claude")


async def basic_chat(user_message: str, system: str = "You are a helpful assistant.") -> str:
    """Single-turn using Agent SDK — collects all text from assistant events."""
    full_response = ""

    # query() is an ASYNC GENERATOR — you must iterate with async for
    async for event in claude_agent_sdk.query(
        prompt=user_message,
        options=claude_agent_sdk.ClaudeCodeOptions(
            system_prompt=system,
            max_turns=1,            # 1 turn = no agentic looping needed here
            model=ANTHROPIC_MODEL,
        )
    ):
        # Each event has a .type attribute
        if event.type == "assistant":
            # event.message.content is a list of content blocks
            for block in event.message.content:
                if hasattr(block, "text"):
                    full_response += block.text

        elif event.type == "result":
            # Final event — has cost/duration info
            # event.total_cost_usd, event.duration_ms
            pass

    return full_response.strip()


async def main():
    header("Claude Agent SDK (claude-agent-sdk)", "01 — Basic Chat", ANTHROPIC_MODEL)

    print("Q: What is the speed of light?")
    answer = await basic_chat("What is the speed of light in km/s? One sentence only.")
    print("A:", answer)

    print("\nQ: Explain recursion (pirate persona)")
    pirate = await basic_chat(
        "Explain recursion in programming.",
        system="You are a pirate. Answer in pirate speak, max 2 sentences."
    )
    print("A:", pirate)

    # ── What you learn here ──────────────────────────────────────────────────
    # 1. Agent SDK is ASYNC ONLY — requires asyncio.run() or an event loop
    # 2. You iterate events, not a single response object
    # 3. For basic chat, the overhead (event loop + event parsing) is NOT worth it
    # 4. The Agent SDK shines in UC08+ (multi-agent, file ops, shell commands)
    # 5. result event gives you cost data without accessing response.usage manually

    print("\n── WHEN TO USE AGENT SDK FOR CHAT ──")
    print("✗ Basic single Q&A       → use Claude SDK (simpler)")
    print("✗ Streaming chat UI      → use Claude SDK with stream=True")
    print("✓ Agent with file access → Agent SDK is the right tool")
    print("✓ Shell command agents   → Agent SDK is the right tool")
    print("✓ Code writing agents    → Agent SDK is the right tool")


if __name__ == "__main__":
    asyncio.run(main())
