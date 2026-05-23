"""
UC10 — Human-in-the-Loop | Claude SDK
══════════════════════════════════════
KEY INSIGHT — Human-in-the-loop with Claude SDK:
  Claude SDK gives you a raw agentic loop — which means YOU decide
  when to pause and ask the human for approval.

  The pattern:
    1. Run the agent loop normally
    2. Before executing a "sensitive" tool, PAUSE
    3. Show the human: "Claude wants to call X with args Y"
    4. Wait for human input: approve / reject / modify
    5. Continue or abort based on human decision

  This is the MOST FLEXIBLE approach — you control exactly when
  and how the human is consulted. You can:
    - Require approval for specific tool names
    - Require approval above a cost threshold
    - Require approval for destructive operations
    - Show the human a diff and ask "apply this change?"

  The tradeoff: you build all this logic yourself.
  LangGraph gives you interrupt_before= for free.

  REAL USE CASES:
    - "Delete all files matching *.tmp" → approve before delete
    - "Send email to all 500 users" → approve the draft first
    - "Execute this SQL query" → show query, approve before run
    - "Charge $500 to the card" → human must approve payment
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ── Which tools require human approval ───────────────────────────────────────

SENSITIVE_TOOLS = {
    "send_email",     # irreversible — once sent, can't unsend
    "get_stock_price" # simulating a "place order" type action
}


def human_approve(tool_name: str, tool_input: dict) -> tuple[bool, dict]:
    """
    Pause execution and ask the human whether to proceed.
    Returns (approved: bool, possibly_modified_input: dict)

    In production this could be:
      - A web UI modal
      - A Slack message with approve/deny buttons
      - A terminal prompt (as shown here)
      - A mobile push notification
    """
    print(f"\n{'═'*60}")
    print(f"  ⚠️  HUMAN APPROVAL REQUIRED")
    print(f"{'═'*60}")
    print(f"  Tool:  {tool_name}")
    print(f"  Input: {json.dumps(tool_input, indent=2)}")
    print(f"{'─'*60}")
    print(f"  Options:")
    print(f"    [y] Approve and execute")
    print(f"    [n] Reject — tell Claude this was denied")
    print(f"    [m] Modify the input before executing")
    print(f"{'═'*60}")

    choice = input("  Your choice [y/n/m]: ").strip().lower()

    if choice == "y":
        return True, tool_input
    elif choice == "m":
        print("  Current input (edit as JSON):")
        print(f"  {json.dumps(tool_input)}")
        modified_str = input("  Modified input JSON: ").strip()
        try:
            modified_input = json.loads(modified_str)
            return True, modified_input
        except json.JSONDecodeError:
            print("  Invalid JSON — rejecting")
            return False, tool_input
    else:
        return False, tool_input


def run_agent_with_hitl(task: str, auto_approve: bool = False) -> str:
    """
    Full agentic loop with human-in-the-loop gate on sensitive tools.

    auto_approve=True skips the interactive prompt (for demo/testing).
    """
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": task}]
    iteration = 0

    print(f"\nTask: {task}")

    while iteration < 10:
        iteration += 1
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=(
                "You are a helpful assistant with access to tools. "
                "Be clear about what you're doing before calling tools."
            ),
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )

        # ── Agent finished ────────────────────────────────────────────────
        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            return final_text

        # ── Agent wants to call tools ─────────────────────────────────────
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name  = block.name
                tool_input = block.input

                # ── HUMAN-IN-THE-LOOP GATE ────────────────────────────────
                if tool_name in SENSITIVE_TOOLS and not auto_approve:
                    approved, final_input = human_approve(tool_name, tool_input)

                    if not approved:
                        # Tell Claude the action was denied by the human
                        denial_msg = (
                            f"Action DENIED by human operator. "
                            f"The tool '{tool_name}' was not executed. "
                            f"Please adjust your approach accordingly."
                        )
                        print(f"\n  [HITL] ✗ Denied: {tool_name}")
                        tool_results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     denial_msg,
                            "is_error":    True,
                        })
                        continue

                    # Human approved (possibly with modified input)
                    print(f"\n  [HITL] ✓ Approved: {tool_name}")
                    tool_input = final_input
                else:
                    print(f"  [Auto] Running: {tool_name}({tool_input})")

                # Execute the tool
                result = execute_tool(tool_name, tool_input)
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     str(result),
                })

            messages.append({"role": "user", "content": tool_results})

    return "Max iterations reached."


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "10 — Human-in-the-Loop", ANTHROPIC_MODEL)

    print("\n── DEMO: Human approval required for send_email ──")
    print("   (running in auto_approve=True mode for non-interactive demo)")
    print("   Set auto_approve=False in code for real interactive approval\n")

    tasks = [
        # Non-sensitive — runs automatically
        "What is the weather in London and Tokyo?",

        # Sensitive — requires human approval (auto-approved in demo)
        "Get the NVIDIA stock price and send an email to team@company.com "
        "with the current price.",
    ]

    for task in tasks:
        result = run_agent_with_hitl(task, auto_approve=True)
        print(f"\nResult: {result[:300]}\n{'─'*60}")

    print("\n── CLAUDE SDK HITL PATTERN ──")
    print("Gate: check tool_name in SENSITIVE_TOOLS before execute_tool()")
    print("Human decision: approve / reject / modify input")
    print("Rejection: send is_error tool_result back to Claude")
    print("Claude adapts: adjusts plan based on denial message")
    print("Full control: you own every decision about what needs approval")
