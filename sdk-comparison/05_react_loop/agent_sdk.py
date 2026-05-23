"""
UC05 — ReAct Loop | Claude Agent SDK
══════════════════════════════════════
KEY INSIGHT — Agent SDK IS a ReAct loop:
  The Agent SDK's query() IS a ReAct loop, fully managed.
  When you set max_turns=10, you're saying:
  "Allow up to 10 think-act-observe cycles before stopping."

  Each "turn" in the Agent SDK corresponds to one full ReAct iteration:
    - Claude thinks (no event emitted for pure thinking)
    - Claude acts (tool call event)
    - Agent SDK observes (executes tool, feeds result back)
    - Claude decides next action

  For complex ReAct tasks, the Agent SDK is the most concise code.
  The tradeoff: you can't inject custom logic between steps.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"

REACT_SYSTEM = """You are a research and analysis assistant with access to Bash.
Use Python via Bash to calculate things. Think step by step.
For each sub-task, use the appropriate tool.
"""


async def run_react(prompt: str, max_turns: int = 10) -> str:
    print(f"\n{'━'*60}")
    print(f"Task: {prompt}")
    print(f"{'━'*60}")

    final_answer = ""
    turn_count = 0

    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=max_turns,
            system_prompt=REACT_SYSTEM,
            allowed_tools=["Bash"],
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    final_answer = block.text
                    print(f"[Assistant] {block.text[:150]}")
                elif hasattr(block, "name"):
                    print(f"[Tool: {block.name}] input={str(getattr(block,'input',{}))[:60]}")

        elif event.type == "result":
            turn_count = getattr(event, "num_turns", "?")
            print(f"\n[Result] Completed in {turn_count} turns, "
                  f"stop={event.stop_reason}")

    print(f"\n{'━'*60}")
    print(f"FINAL ANSWER (after {turn_count} turns):")
    print(f"{'━'*60}")
    return final_answer


async def main():
    header("Claude Agent SDK", "05 — ReAct Loop", ANTHROPIC_MODEL)

    result = await run_react(
        "Investment analysis task:\n"
        "1. Calculate $10,000 at 15% growth for 3 years: python3 -c \"print(10000*(1.15**3))\"\n"
        "2. Calculate $10,000 at 25% growth for 3 years: python3 -c \"print(10000*(1.25**3))\"\n"
        "3. Calculate the difference between the two\n"
        "4. Give me the final comparison and recommendation",
        max_turns=8,
    )
    print(result)

    print("\n── AGENT SDK ReAct ADVANTAGE ──")
    print("Most concise ReAct implementation of all 4 SDKs")
    print("max_turns controls the loop depth")
    print("Bash tool = Python execution = full computation power")
    print("Tradeoff: can't inject custom logic between steps")
    print("         can't modify state mid-loop")
    print("         can't conditionally route to different agents")


if __name__ == "__main__":
    asyncio.run(main())
