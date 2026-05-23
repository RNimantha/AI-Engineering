"""
UC05 — ReAct Loop | OpenAI Python SDK
══════════════════════════════════════
KEY INSIGHT — Same pattern, same power, different syntax.
  OpenAI's ReAct loop is structurally identical to Claude's.
  The differences are purely syntactic (finish_reason vs stop_reason,
  choices[0].message vs response.content, etc.)

  One unique OpenAI feature shown here: o1/o1-mini reasoning models
  These models do chain-of-thought INTERNALLY before responding.
  For ReAct tasks, you can use gpt-4o for tool-calling loops
  and reserve o1 for the final synthesis step (hybrid approach).
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"

REACT_SYSTEM = """You are a research and analysis assistant.
Think step by step. Use tools to gather information before answering.
Never guess — always use tools to get real data.
"""


def run_react(user_message: str, max_turns: int = 10) -> str:
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user",   "content": user_message},
    ]

    print(f"\n{'━' * 60}")
    print(f"Task: {user_message}")
    print(f"{'━' * 60}")

    turn = 0
    while turn < max_turns:
        turn += 1
        print(f"\n[Turn {turn}]")

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            messages=messages,
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason
        print(f"  finish_reason: {finish}")

        if finish == "stop":
            print(f"\n{'━' * 60}")
            print(f"FINAL ANSWER (after {turn} turns):")
            print(f"{'━' * 60}")
            return msg.content

        if finish == "tool_calls":
            messages.append(msg)

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"  [Tool] {name}({str(args)[:60]})")
                result = execute_tool(name, args)
                print(f"  [→] {result[:150]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
        else:
            break

    return "Max turns reached"


if __name__ == "__main__":
    header("OpenAI Python SDK", "05 — ReAct Loop", OPENAI_MODEL)

    result = run_react(
        "I want to make an investment decision. "
        "Check AAPL and NVDA stock prices, search for 'best tech stocks 2025', "
        "then calculate: if I invest $10,000 in AAPL (15% growth) vs NVDA (25% growth) "
        "for 3 years (formula: 10000*(1+rate)**3), "
        "which would be worth more, and by how much?"
    )
    print(result)

    print("\n── OPENAI vs CLAUDE REACT DIFF ──")
    print("Structure: IDENTICAL")
    print("Claude: stop_reason='tool_use' → response.content[i].type=='tool_use'")
    print("OpenAI: finish_reason='tool_calls' → msg.tool_calls[i].function.name")
    print()
    print("The loop logic is the same. The API surface differs slightly.")
