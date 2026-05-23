"""
UC10 — Human-in-the-Loop | Claude Agent SDK
════════════════════════════════════════════
KEY INSIGHT — Human-in-the-loop with Claude Agent SDK:
  The Agent SDK exposes two built-in HITL mechanisms:

  1. permission_mode = "acceptEdits" | "bypassPermissions" | "default"
       - "default": Claude Code's normal permission prompts
       - "acceptEdits": auto-accepts file edits (but still prompts for others)
       - "bypassPermissions": skips ALL permission prompts (DANGEROUS in prod)

  2. Custom permission_prompt_tool_name (advanced):
       You can supply an MCP tool that the agent calls whenever it needs
       permission for a sensitive operation. That MCP tool can route
       the request to a Slack bot, a web UI, or even another LLM that
       acts as a "safety supervisor".

  3. Manual HITL between turns:
       Since the Agent SDK is an async generator, you can pause BETWEEN
       turn boundaries and inject human decisions as new prompts.
       This is the pattern shown here.

  AGENT SDK vs CLAUDE SDK for HITL:
    Claude SDK:  pause MID-tool-loop (before individual tool calls)
    Agent SDK:   pause BETWEEN turns (between assistant responses)
    LangGraph:   interrupt_before specific nodes (most granular)

  The Agent SDK's turn-based model means you can:
    - Inspect each assistant message as it arrives
    - Decide whether to continue, redirect, or stop
    - Inject human corrections as follow-up prompts
    - Build approval workflows that span multiple turns
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ── Keywords that trigger a human review ─────────────────────────────────────

SENSITIVE_KEYWORDS = ["email", "send", "delete", "remove", "purchase", "pay", "execute"]


def contains_sensitive_action(text: str) -> bool:
    """Check if assistant output mentions a sensitive action."""
    lower = text.lower()
    return any(kw in lower for kw in SENSITIVE_KEYWORDS)


# ── Pattern 1: Turn-based HITL ───────────────────────────────────────────────

async def run_with_turn_approval(initial_task: str, auto_approve: bool = False) -> str:
    """
    Run agent turn by turn. After each assistant message, check if human
    approval is needed before continuing.
    """
    print(f"\nTask: {initial_task}")

    current_prompt = initial_task
    session_id = None
    final_result = ""
    turn = 0

    while turn < 5:
        turn += 1
        print(f"\n  [Turn {turn}] Running agent...")

        async for event in claude_agent_sdk.query(
            prompt=current_prompt,
            options=claude_agent_sdk.ClaudeCodeOptions(
                model=ANTHROPIC_MODEL,
                max_turns=1,           # ← one turn at a time for HITL
                session_id=session_id,
                resume=session_id is not None,
                system_prompt=(
                    "You are a helpful assistant. Think step-by-step. "
                    "Before taking any sensitive action (sending emails, "
                    "deleting files, making purchases), explicitly describe "
                    "what you're about to do and wait for confirmation."
                ),
                allowed_tools=["Bash"],
                permission_mode="default",
            )
        ):
            if event.type == "system" and hasattr(event, "session_id"):
                session_id = event.session_id

            elif event.type == "assistant":
                for block in event.message.content:
                    if hasattr(block, "text") and block.text:
                        text = block.text
                        print(f"  [Claude]: {text[:150]}...")
                        final_result = text

                        # ── HUMAN-IN-THE-LOOP GATE ────────────────────────
                        if contains_sensitive_action(text) and not auto_approve:
                            print(f"\n{'═'*60}")
                            print(f"  ⚠️  Claude is about to take a sensitive action.")
                            print(f"{'─'*60}")
                            print(f"  Claude said: \"{text[:200]}\"")
                            print(f"{'─'*60}")
                            print(f"  [y] Continue  [n] Stop  [r] Redirect")
                            choice = input("  Your choice: ").strip().lower()

                            if choice == "n":
                                print("  [HITL] Stopping agent.")
                                return final_result + "\n[Stopped by human]"
                            elif choice == "r":
                                redirect = input("  New instruction for Claude: ").strip()
                                current_prompt = redirect
                                break  # restart loop with new prompt
                            else:
                                print("  [HITL] ✓ Approved — continuing.")

            elif event.type == "result":
                if hasattr(event, "result") and event.result:
                    final_result = event.result
                print(f"  [Done after turn {turn}]")
                # If result is complete, stop
                return final_result

    return final_result


# ── Pattern 2: Permission mode demonstration ─────────────────────────────────

async def run_with_bypass_permissions(task: str) -> str:
    """
    bypassPermissions=True: skip ALL built-in permission prompts.
    Use ONLY in sandboxed/trusted environments.

    This is the inverse of HITL — you're telling the SDK
    "I trust this agent completely, don't ask me anything."
    """
    text = ""
    async for event in claude_agent_sdk.query(
        prompt=task,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=3,
            system_prompt="You are a helpful assistant.",
            allowed_tools=["Bash"],
            permission_mode="bypassPermissions",   # ← NO prompts at all
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    text = block.text
    return text


# ── Pattern 3: Inject human feedback mid-session ─────────────────────────────

async def run_with_feedback_injection(task: str) -> str:
    """
    Run one turn, inspect the plan, inject a correction, run again.
    Classic "draft → review → revise" workflow.
    """
    print(f"\nTask: {task}")

    # Turn 1: Generate a plan
    plan_text = ""
    session_id = None

    async for event in claude_agent_sdk.query(
        prompt=f"Plan (don't execute yet): {task}",
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL, max_turns=1,
            system_prompt="Create a numbered plan. Do NOT execute yet.",
            allowed_tools=[],
        )
    ):
        if event.type == "system" and hasattr(event, "session_id"):
            session_id = event.session_id
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    plan_text = block.text

    print(f"\n  [Claude's Plan]:\n{plan_text}")

    # Human reviews the plan (auto-approved in demo)
    print(f"\n  [HITL] Review Claude's plan above.")
    print(f"  Press Enter to approve, or type a correction:")
    if not True:  # set to False for interactive mode
        correction = input("  > ").strip()
        if correction:
            feedback = f"Revised plan: {correction}"
        else:
            feedback = "Plan approved. Execute it now."
    else:
        feedback = "Plan approved. Execute it now."
        print(f"  [Auto-approved] → '{feedback}'")

    # Turn 2: Execute with human feedback incorporated
    result_text = ""
    async for event in claude_agent_sdk.query(
        prompt=feedback,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL, max_turns=3,
            session_id=session_id,
            resume=True,
            system_prompt="Execute the plan as approved by the human.",
            allowed_tools=["Bash"],
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    result_text = block.text

    return result_text


async def main():
    header("Claude Agent SDK", "10 — Human-in-the-Loop", ANTHROPIC_MODEL)

    print("\n── Pattern 1: Turn-based approval ──")
    result1 = await run_with_turn_approval(
        "Calculate the square root of 144, then describe what email you would "
        "send to summarize the result.",
        auto_approve=True
    )
    print(f"\nResult: {result1[:200]}")

    print("\n\n── Pattern 3: Plan → Review → Execute ──")
    result3 = await run_with_feedback_injection(
        "Write a Python function to calculate compound interest."
    )
    print(f"\nFinal: {result3[:200]}")

    print("\n── AGENT SDK HITL PATTERNS ──")
    print("Turn-based:         max_turns=1, loop manually, pause between turns")
    print("Permission mode:    'default' | 'acceptEdits' | 'bypassPermissions'")
    print("Feedback injection: session_id + resume=True to continue with corrections")
    print("Custom approver:    permission_prompt_tool_name → MCP tool → Slack/UI")


if __name__ == "__main__":
    asyncio.run(main())
