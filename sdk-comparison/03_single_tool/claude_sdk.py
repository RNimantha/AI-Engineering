"""
UC03 — Single Tool | Claude SDK (anthropic)
════════════════════════════════════════════
KEY INSIGHT — Tool use with Claude SDK:
  This is where agentic behaviour begins. Instead of just generating text,
  the model can CALL FUNCTIONS you define.

  The agentic loop (manual — you write it):
    1. Send message + tool definitions to Claude
    2. Claude returns stop_reason="tool_use" + a ToolUseBlock
    3. You execute the tool locally
    4. You append the result as a "tool_result" message
    5. You call Claude again — it generates the final text answer
    6. Claude returns stop_reason="end_turn" → done

  This loop is the foundation of ALL agentic behaviour.
  Every agent pattern (ReAct, supervisor, multi-agent) is a variation of it.

  KEY STRUCTURAL NOTE:
    Tool definition format uses "input_schema" (not "parameters")
    Tool results are sent as: {"role":"user","content":[{"type":"tool_result",...}]}
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Use only the calculator tool for this example
CALC_TOOL = [t for t in ANTHROPIC_TOOLS if t["name"] == "calculate"]


def run_with_tool(user_message: str) -> str:
    """
    Complete agentic loop with one tool.
    Returns Claude's final natural-language answer after using the tool.
    """
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))

    messages = [{"role": "user", "content": user_message}]

    print(f"\nUser: {user_message}")

    while True:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            tools=CALC_TOOL,
            messages=messages,
        )

        print(f"[stop_reason: {response.stop_reason}]")

        # ── End of conversation ──
        if response.stop_reason == "end_turn":
            # Extract the final text answer
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        # ── Claude wants to use a tool ──
        if response.stop_reason == "tool_use":
            # Append Claude's response (which contains the tool_use block)
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call in the response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[Tool call] {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"[Tool result] {result}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,     # ← Must match the tool_use block's id
                        "content": result,
                    })

            # Append tool results as a user message
            messages.append({"role": "user", "content": tool_results})
            # Loop continues → Claude sees the result and generates final answer

        else:
            # Unexpected stop reason
            break

    return "Unexpected end of loop"


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "03 — Single Tool (Calculator)", ANTHROPIC_MODEL)

    # Test 1: Basic arithmetic
    print(run_with_tool("What is 1337 * 42?"))

    # Test 2: Compound interest formula
    print(run_with_tool(
        "If I invest $10,000 at 7% annual return for 20 years, "
        "what will it be worth? Use the formula: 10000 * (1.07 ** 20)"
    ))

    # Test 3: Multi-step math
    print(run_with_tool(
        "What is the hypotenuse of a right triangle with legs 5 and 12? "
        "Use: sqrt(5**2 + 12**2)"
    ))

    print("\n── AGENTIC LOOP ANATOMY ──")
    print("1. User message + tool defs → Claude")
    print("2. Claude: stop_reason='tool_use', content=[ToolUseBlock]")
    print("3. You: execute tool, get result")
    print("4. You: append result as messages=[{role:'user',content:[{type:'tool_result'}]}]")
    print("5. Claude: stop_reason='end_turn', content=[TextBlock]")
    print("   → This loop is the DNA of ALL agentic patterns")
