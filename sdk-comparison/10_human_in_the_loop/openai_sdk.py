"""
UC10 — Human-in-the-Loop | OpenAI Python SDK
══════════════════════════════════════════════
KEY INSIGHT — Human-in-the-loop with OpenAI SDK:
  The OpenAI SDK, like the Claude SDK, gives you a raw agentic loop.
  HITL is implemented manually by inspecting tool_calls BEFORE executing them.

  The pattern mirrors Claude SDK's approach:
    finish_reason == "tool_calls" → inspect each tool call
    → if sensitive: pause and ask human
    → if approved:  execute and continue
    → if rejected:  send error tool result back to the model

  KEY DIFFERENCE from Claude SDK:
    OpenAI tool args are JSON STRINGS → need json.loads()
    Claude tool args are Python dicts  → use directly

  ADDITIONAL OpenAI-SPECIFIC PATTERNS:
    1. "require_action" in Assistants API — the Assistants API has a
       native HITL hook: when run.status == "requires_action",
       the run pauses and waits for you to submit tool outputs.
       This is OpenAI's closest native equivalent to LangGraph's
       interrupt_before. (Shown conceptually below.)

    2. Structured approval context: Since OpenAI has parallel tool calls,
       you may need to approve/reject multiple tools in one batch.

  REAL PRODUCTION PATTERNS:
    - Approve before "send_email" (irreversible)
    - Approve before "delete_record" (destructive)
    - Approve before "make_payment" (financial)
    - Show diff before "update_file" (risky mutation)
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"

# ── Which tools require human approval ───────────────────────────────────────

SENSITIVE_TOOLS = {"send_email", "get_stock_price"}

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.
When planning to use a sensitive tool (like sending emails or financial operations),
briefly describe what you intend to do first, then proceed."""


def human_approve(tool_name: str, tool_input: dict) -> tuple[bool, dict]:
    """
    Interactive terminal approval gate.
    Returns (approved, final_input).
    """
    print(f"\n{'═'*60}")
    print(f"  ⚠️  HUMAN APPROVAL REQUIRED")
    print(f"{'═'*60}")
    print(f"  Tool  : {tool_name}")
    print(f"  Input : {json.dumps(tool_input, indent=2)}")
    print(f"{'─'*60}")
    print(f"  [y] Approve   [n] Reject   [m] Modify input")
    print(f"{'═'*60}")

    choice = input("  Choice [y/n/m]: ").strip().lower()

    if choice == "y":
        return True, tool_input
    elif choice == "m":
        raw = input(f"  Modified JSON: ").strip()
        try:
            return True, json.loads(raw)
        except json.JSONDecodeError:
            print("  Invalid JSON — rejecting.")
            return False, tool_input
    else:
        return False, tool_input


def run_agent_with_hitl(task: str, auto_approve: bool = False) -> str:
    """
    OpenAI agentic loop with human approval gate on sensitive tools.
    """
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": task},
    ]

    print(f"\nTask: {task}")
    iteration = 0

    while iteration < 10:
        iteration += 1

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            messages=messages,
        )

        msg    = response.choices[0].message
        reason = response.choices[0].finish_reason

        # ── Agent finished ────────────────────────────────────────────────
        if reason == "stop":
            return msg.content or ""

        # ── Agent wants to call tools ─────────────────────────────────────
        if reason == "tool_calls":
            messages.append(msg)   # append assistant message with tool_calls

            for tc in msg.tool_calls:
                tool_name  = tc.function.name
                # OpenAI args are JSON strings — must parse!
                tool_input = json.loads(tc.function.arguments)

                # ── HUMAN-IN-THE-LOOP GATE ────────────────────────────────
                if tool_name in SENSITIVE_TOOLS and not auto_approve:
                    approved, final_input = human_approve(tool_name, tool_input)

                    if not approved:
                        denial = (
                            f"DENIED: The human operator rejected the call to "
                            f"'{tool_name}'. Do not retry this action. "
                            f"Adjust your plan and inform the user."
                        )
                        print(f"  [HITL] ✗ Denied: {tool_name}")
                        messages.append({
                            "role":         "tool",
                            "tool_call_id": tc.id,
                            "content":      denial,
                        })
                        continue

                    print(f"  [HITL] ✓ Approved: {tool_name}")
                    tool_input = final_input
                else:
                    print(f"  [Auto] {tool_name}({tool_input})")

                # Execute and append result
                result = execute_tool(tool_name, tool_input)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      str(result),
                })

        else:
            break

    return "Max iterations reached."


# ── Conceptual: OpenAI Assistants API native HITL ─────────────────────────────

def assistants_api_hitl_concept():
    """
    NOTE: This function is CONCEPTUAL — not runnable without an Assistant ID.

    The Assistants API has a NATIVE human-in-the-loop hook:

        run = client.beta.threads.runs.create(...)

        while run.status in ("queued", "in_progress", "requires_action"):
            run = client.beta.threads.runs.retrieve(run.id)

            if run.status == "requires_action":
                # ← THE NATIVE PAUSE POINT
                tool_outputs = []
                for tc in run.required_action.submit_tool_outputs.tool_calls:
                    # Human approval check here
                    approved, result = approve_and_run(tc)
                    tool_outputs.append({
                        "tool_call_id": tc.id,
                        "output": result if approved else "DENIED"
                    })
                # Resume the run with results
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=run.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                )

    This is analogous to LangGraph's interrupt_before — the run
    PAUSES at tool execution and waits for you to submit outputs.
    You have full control over what output to inject.
    """
    pass


if __name__ == "__main__":
    header("OpenAI Python SDK", "10 — Human-in-the-Loop", OPENAI_MODEL)

    print("Running in auto_approve=True mode for demo.")
    print("Set auto_approve=False for interactive terminal approval.\n")

    tasks = [
        # Safe — auto-executes
        "What is the weather in Paris and New York?",

        # Sensitive — would require approval if auto_approve=False
        "Look up NVIDIA's stock price and send a summary email to cto@company.com.",
    ]

    for task in tasks:
        result = run_agent_with_hitl(task, auto_approve=True)
        print(f"\nResult: {result[:300]}\n{'─'*60}")

    print("\n── OPENAI SDK HITL vs CLAUDE SDK HITL ──")
    print("Structure:    both gate on sensitive tool names in the loop")
    print("Args format:  OpenAI → json.loads(str)  |  Claude → dict directly")
    print("Tool result:  OpenAI → role='tool'       |  Claude → type='tool_result'")
    print("Rejection:    both send error message back so model can adapt")
    print("Native HITL:  Assistants API requires_action is OpenAI's pause hook")
    print("Best HITL:    LangGraph interrupt_before= — declarative, resumable")
