"""
UC03 — Single Tool | OpenAI Python SDK
══════════════════════════════════════════
KEY INSIGHT — Tool use with OpenAI SDK:
  Very similar loop to Claude SDK but with different field names.

  DIFF TABLE:
  ┌──────────────────┬────────────────────────┬────────────────────────┐
  │                  │ Claude SDK             │ OpenAI SDK             │
  ├──────────────────┼────────────────────────┼────────────────────────┤
  │ Tool schema key  │ "input_schema"         │ "parameters"           │
  │ Stop signal      │ stop_reason="tool_use" │ finish_reason="tool_calls" │
  │ Tool block       │ response.content[i]    │ response.choices[0].message.tool_calls[i] │
  │ Tool name        │ block.name             │ tool_call.function.name │
  │ Tool args        │ block.input (dict)     │ tool_call.function.arguments (JSON STRING) │
  │ Tool ID          │ block.id               │ tool_call.id           │
  │ Result message   │ role:"user", type:"tool_result" │ role:"tool" │
  └──────────────────┴────────────────────────┴────────────────────────┘

  ⚠️ OpenAI GOTCHA: tool_call.function.arguments is a JSON STRING, not a dict!
  You must json.loads() it before passing to your function.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"

CALC_TOOL_OPENAI = [t for t in OPENAI_TOOLS if t["function"]["name"] == "calculate"]


def run_with_tool(user_message: str) -> str:
    """Complete OpenAI agentic loop with one tool."""
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))

    messages = [
        {"role": "system", "content": "You are a helpful math assistant."},
        {"role": "user",   "content": user_message},
    ]

    print(f"\nUser: {user_message}")

    while True:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            tools=CALC_TOOL_OPENAI,
            tool_choice="auto",        # "auto" = Claude picks whether to use tool
            messages=messages,
        )

        msg = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        print(f"[finish_reason: {finish_reason}]")

        # ── Done ──
        if finish_reason == "stop":
            return msg.content

        # ── Tool use ──
        if finish_reason == "tool_calls":
            # Append assistant message (contains tool_calls)
            messages.append(msg)   # msg is ChatCompletionMessage, not a dict

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                # ⚠️ arguments is a JSON STRING — must parse it!
                tool_args = json.loads(tool_call.function.arguments)

                print(f"[Tool call] {tool_name}({tool_args})")
                result = execute_tool(tool_name, tool_args)
                print(f"[Tool result] {result}")

                # Tool result goes as role="tool" (not role="user" like Claude)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,   # must match
                    "content":      result,
                })

        else:
            break

    return "Unexpected end"


if __name__ == "__main__":
    header("OpenAI Python SDK", "03 — Single Tool (Calculator)", OPENAI_MODEL)

    print(run_with_tool("What is 1337 * 42?"))
    print(run_with_tool(
        "If I invest $10,000 at 7% annual return for 20 years, "
        "what will it be worth? Use: 10000 * (1.07 ** 20)"
    ))
    print(run_with_tool("What is sqrt(5**2 + 12**2)?"))

    print("\n── CRITICAL DIFF: Tool args ──")
    print("Claude SDK: block.input              → already a Python DICT")
    print("OpenAI SDK: tool_call.function.arguments → JSON STRING → json.loads() needed")
    print()
    print("── CRITICAL DIFF: Tool result message ──")
    print("Claude SDK: {role:'user', content:[{type:'tool_result', tool_use_id:...}]}")
    print("OpenAI SDK: {role:'tool', tool_call_id:..., content:...}")
