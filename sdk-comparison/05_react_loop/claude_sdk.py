"""
UC05 — ReAct Loop | Claude SDK (anthropic)
════════════════════════════════════════════
KEY INSIGHT — ReAct (Reason + Act):
  ReAct is the foundational agentic pattern:
    Reason:  "I need to find X, then calculate Y, then compare Z"
    Act:     call tool X, get result, call tool Y, get result
    Observe: incorporate results into next reasoning step
    Repeat:  until the goal is achieved

  This is NOT new code — the same loop from UC03/UC04 IS the ReAct loop.
  What changes is:
    1. The PROMPT: you explicitly ask Claude to think step-by-step
    2. The COMPLEXITY: the task requires 3-5 tool calls in sequence
       where each call's result informs the next call
    3. The TURN COUNT: you need enough turns (max_iterations) to complete

  The key insight: Claude doesn't just call tools randomly.
  It REASONS about what information it needs, decides which tool
  gets it closer to the answer, observes the result, and adapts.
  That reasoning-adaptation cycle is what makes it "agentic."
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"

REACT_SYSTEM_PROMPT = """You are a research and analysis assistant.

For complex questions, use this approach:
1. THINK: What information do I need? Break the problem into steps.
2. ACT: Call the appropriate tool to get that information.
3. OBSERVE: What did the tool return? Does it answer part of the question?
4. REPEAT: What do I still need? Call another tool if necessary.
5. ANSWER: Synthesize all gathered information into a final, complete answer.

Always show your reasoning. Never guess — use tools to get real data.
"""


def run_react(user_message: str, max_turns: int = 10) -> str:
    """
    Full ReAct loop: multi-step reasoning with tool use.
    max_turns prevents infinite loops.
    """
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": user_message}]

    print(f"\n{'━' * 60}")
    print(f"Task: {user_message}")
    print(f"{'━' * 60}")

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n[Turn {turn}]")

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=REACT_SYSTEM_PROMPT,
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )

        print(f"  stop_reason: {response.stop_reason}")

        # Print any thinking/reasoning text blocks
        for block in response.content:
            if hasattr(block, "text") and response.stop_reason != "end_turn":
                print(f"  [Reasoning] {block.text[:200]}")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n{'━' * 60}")
                    print(f"FINAL ANSWER (after {turn} turns):")
                    print(f"{'━' * 60}")
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [Tool] {block.name}({json.dumps(block.input)[:60]})")
                    result = execute_tool(block.name, block.input)
                    print(f"  [→ Result] {result[:150]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

    return f"Max turns ({max_turns}) reached without final answer"


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "05 — ReAct Loop", ANTHROPIC_MODEL)

    # Complex task requiring 4+ tool calls in a logical sequence
    result = run_react(
        "I want to make an investment decision. "
        "Check AAPL and NVDA stock prices, search for 'best tech stocks 2025', "
        "then calculate: if I invest $10,000 in AAPL vs $10,000 in NVDA "
        "and AAPL grows 15% while NVDA grows 25% over 3 years "
        "(formula: 10000 * (1+rate)**3 for each), "
        "which investment would be worth more, and by how much?"
    )
    print(result)

    print("\n── REACT LOOP INSIGHT ──")
    print("Turn 1: Claude reasons 'I need stock prices first'")
    print("Turn 2: Claude calls get_stock_price(AAPL), get_stock_price(NVDA) [parallel]")
    print("Turn 3: Claude calls search_web('best tech stocks 2025')")
    print("Turn 4: Claude calls calculate('10000 * 1.15**3'), calculate('10000 * 1.25**3')")
    print("Turn 5: Claude synthesizes → final answer")
    print()
    print("This is the ReAct loop — same code as UC03, harder task.")
