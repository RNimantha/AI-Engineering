"""
UC04 — Multi-Tool | Claude SDK (anthropic)
═══════════════════════════════════════════
KEY INSIGHT — Multiple tools + parallel tool calls:
  The same loop from UC03 handles multiple tools automatically.
  Claude decides WHICH tool to call and CAN call multiple tools
  in a single turn (parallel tool use).

  Parallel tool use:
    Claude may return MULTIPLE ToolUseBlocks in one response.
    You must process ALL of them before continuing the loop.
    This is more efficient than sequential: Claude calls
    get_weather(London) AND get_weather(Tokyo) simultaneously,
    rather than asking you to run them one at a time.

  New concepts:
    - Multiple tool definitions passed at once
    - response.content can have MULTIPLE tool_use blocks
    - tool_choice param: "auto" | "any" | {"type":"tool","name":"..."}
      "any"  = Claude MUST use at least one tool
      "auto" = Claude decides whether to use tools
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"


def run_agent(user_message: str, verbose: bool = True) -> str:
    """Multi-tool agentic loop — identical structure to UC03, now with N tools."""
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": user_message}]

    if verbose:
        print(f"\nUser: {user_message}")

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            tools=ANTHROPIC_TOOLS,          # all 5 tools available
            tool_choice={"type": "auto"},   # Claude decides when/which to use
            messages=messages,
        )

        if verbose:
            print(f"[stop_reason: {response.stop_reason}]")

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            # ── KEY: process ALL tool_use blocks (may be parallel calls) ──
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"[Tool] {block.name}({json.dumps(block.input)[:80]})")
                    result = execute_tool(block.name, block.input)
                    if verbose:
                        print(f"  → {result[:120]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            break

    return "Loop ended unexpectedly"


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "04 — Multi-Tool", ANTHROPIC_MODEL)

    # Test 1: Two different tools in sequence
    print("=" * 60)
    result = run_agent(
        "What is the weather in London and Tokyo? "
        "Also calculate the temperature difference in Fahrenheit."
    )
    print(f"\nFinal answer:\n{result}")

    # Test 2: Three tools — research + calculate + summarise
    print("\n" + "=" * 60)
    result = run_agent(
        "Search for 'compound interest formula', "
        "then calculate what $5000 at 6% for 15 years gives: 5000 * (1.06 ** 15), "
        "and check AAPL stock price."
    )
    print(f"\nFinal answer:\n{result}")

    # Test 3: Parallel tool calls (Claude calls multiple tools simultaneously)
    print("\n" + "=" * 60)
    result = run_agent(
        "Compare AAPL, MSFT, and NVDA stock prices. "
        "Which has the highest percentage gain today?"
    )
    print(f"\nFinal answer:\n{result}")

    print("\n── PARALLEL TOOL CALL INSIGHT ──")
    print("When Claude sees 3 independent stock lookups, it MAY")
    print("return 3 ToolUseBlocks in ONE response (parallel).")
    print("Your loop handles this — process ALL blocks before continuing.")
