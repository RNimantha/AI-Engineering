"""
UC04 — Multi-Tool | OpenAI Python SDK
═══════════════════════════════════════
KEY INSIGHT — OpenAI parallel tool calls:
  OpenAI also supports parallel tool calls.
  The difference: response.choices[0].message.tool_calls is a LIST.
  When Claude calls tools in parallel, OpenAI does too — same concept,
  slightly different access pattern.

  One important OpenAI-specific feature: parallel_tool_calls=True/False
  You can explicitly DISABLE parallel calls if your tools have side effects
  that must be sequential (e.g., don't send two emails at the same time).
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"


def run_agent(user_message: str, parallel_tools: bool = True, verbose: bool = True) -> str:
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": "You are a helpful assistant with access to tools."},
        {"role": "user",   "content": user_message},
    ]

    if verbose:
        print(f"\nUser: {user_message}")

    while True:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            parallel_tool_calls=parallel_tools,  # ← OpenAI-specific control
            messages=messages,
        )

        msg = response.choices[0].message
        finish = response.choices[0].finish_reason

        if verbose:
            print(f"[finish_reason: {finish}]")

        if finish == "stop":
            return msg.content

        if finish == "tool_calls":
            messages.append(msg)

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)  # ← still a string!

                if verbose:
                    print(f"[Tool] {name}({args})")
                result = execute_tool(name, args)
                if verbose:
                    print(f"  → {result[:120]}")

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      result,
                })
        else:
            break

    return "Unexpected end"


if __name__ == "__main__":
    header("OpenAI Python SDK", "04 — Multi-Tool", OPENAI_MODEL)

    print("=" * 60)
    result = run_agent(
        "What is the weather in London and Tokyo? "
        "Calculate the temperature difference in Fahrenheit."
    )
    print(f"\nFinal:\n{result}")

    print("\n" + "=" * 60)
    print("── Forcing sequential tool calls (parallel_tool_calls=False) ──")
    result2 = run_agent(
        "Compare AAPL, MSFT, and NVDA stock prices.",
        parallel_tools=False
    )
    print(f"\nFinal:\n{result2}")

    print("\n── OPENAI-SPECIFIC: parallel_tool_calls ──")
    print("parallel_tool_calls=True  → model may call tools in parallel")
    print("parallel_tool_calls=False → model calls one tool at a time")
    print("Claude SDK: no equivalent flag — handled by tool_choice")
