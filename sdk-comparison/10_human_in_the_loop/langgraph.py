"""
UC10 — Human-in-the-Loop | LangGraph
══════════════════════════════════════
KEY INSIGHT — LangGraph is the GOLD STANDARD for human-in-the-loop:
  LangGraph was built with HITL as a first-class citizen.
  Every other SDK forces you to implement HITL manually in your loop.
  LangGraph makes it declarative with a single parameter.

  THREE NATIVE HITL MECHANISMS:

  1. interrupt_before=["node_name"]
       The graph PAUSES before that node executes.
       State is persisted to the checkpointer.
       The run can be RESUMED HOURS LATER from a web UI, Slack, email.
       This is NOT possible with Claude/OpenAI SDK manual loops.

  2. interrupt_after=["node_name"]
       Pause AFTER the node, so you can review its output
       before deciding whether to continue.

  3. NodeInterrupt (programmatic)
       Raise NodeInterrupt("message") from inside a node
       for conditional pausing — "pause only if amount > $1000".

  HOW RESUMPTION WORKS:
       app.invoke(None, config)   ← None means "resume from checkpoint"
       app.update_state(config, new_values)  ← inject human correction

  WHY THIS IS POWERFUL:
    - State is fully serialized at the pause point
    - Resume from any client (web, mobile, CLI)
    - Multiple humans can review different steps
    - Audit trail of every pause + human decision
    - Time-travel: replay from any checkpoint

  COMPARE TO OTHER SDKs:
    Claude SDK:    manual if/input() in the tool loop — no persistence
    OpenAI SDK:    same manual approach — no persistence
    Agent SDK:     max_turns=1 + resume= — turn-level, limited
    LangGraph:     interrupt_before/after + checkpointer — production grade
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import NodeInterrupt
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    from shared.tools import get_weather as _g
    import json as j
    return j.dumps(_g(city))


@tool
def get_stock_price(ticker: str) -> str:
    """Get stock price for a ticker symbol."""
    from shared.tools import get_stock_price as _g
    import json as j
    return j.dumps(_g(ticker))


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. SENSITIVE — requires human approval."""
    from shared.tools import send_email as _s
    import json as j
    return j.dumps(_s(to, subject, body))


# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    human_feedback: str          # injected by human after a pause
    requires_approval: bool      # flag set by sensitive_check node


# ── Nodes ─────────────────────────────────────────────────────────────────────

safe_tools      = [get_weather, get_stock_price]
sensitive_tools = [send_email]
all_tools       = safe_tools + sensitive_tools

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(all_tools)

safe_tool_node      = ToolNode(safe_tools)
sensitive_tool_node = ToolNode(sensitive_tools)


def agent_node(state: AgentState) -> dict:
    """Main agent — plans and decides which tools to call."""
    system = SystemMessage(content=(
        "You are a helpful assistant. You have access to weather, stock, "
        "and email tools. Use them to complete the user's request."
    ))

    # Incorporate human feedback if present
    msgs = state["messages"]
    if state.get("human_feedback"):
        msgs = msgs + [HumanMessage(content=f"[Human feedback]: {state['human_feedback']}")]

    response = llm_with_tools.invoke([system] + msgs)
    return {"messages": [response], "human_feedback": ""}


def sensitive_check_node(state: AgentState) -> dict:
    """
    Inspect the last message. If it contains a call to a sensitive tool,
    raise NodeInterrupt to pause the graph and wait for human approval.

    This is Pattern 3 — programmatic conditional interruption.
    """
    last = state["messages"][-1]
    sensitive_names = {t.name for t in sensitive_tools}

    if hasattr(last, "tool_calls") and last.tool_calls:
        for tc in last.tool_calls:
            if tc["name"] in sensitive_names:
                # ── PAUSE HERE ──────────────────────────────────────────
                raise NodeInterrupt(
                    f"Sensitive tool '{tc['name']}' requested with args: "
                    f"{json.dumps(tc['args'])}. "
                    f"Resume to approve or update state to reject."
                )

    return {}   # no interrupt needed


def should_continue(state: AgentState) -> str:
    """Route: call tools, or finish."""
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        # Check if any tool call is for a sensitive tool
        sensitive_names = {t.name for t in sensitive_tools}
        for tc in last.tool_calls:
            if tc["name"] in sensitive_names:
                return "sensitive_tools"
        return "safe_tools"
    return END


# ── Build graph ───────────────────────────────────────────────────────────────

def build_hitl_graph(use_interrupt_before: bool = False):
    """
    Build the HITL graph. Two interrupt strategies shown:

    use_interrupt_before=True:
        Declarative — graph pauses BEFORE sensitive_tools node automatically.
        Best for: always requiring approval for a node.

    use_interrupt_before=False:
        Programmatic — sensitive_check_node raises NodeInterrupt conditionally.
        Best for: approval only when certain conditions are met.
    """
    g = StateGraph(AgentState)

    g.add_node("agent",           agent_node)
    g.add_node("safe_tools",      safe_tool_node)
    g.add_node("sensitive_check", sensitive_check_node)
    g.add_node("sensitive_tools", sensitive_tool_node)

    g.set_entry_point("agent")

    g.add_conditional_edges("agent", should_continue, {
        "safe_tools":      "safe_tools",
        "sensitive_tools": "sensitive_check",   # check BEFORE executing
        END:               END,
    })

    g.add_edge("safe_tools",      "agent")          # safe tools loop back
    g.add_edge("sensitive_check", "sensitive_tools") # after check, execute
    g.add_edge("sensitive_tools", "agent")           # then back to agent

    # Checkpointer is REQUIRED for HITL — stores state at pause point
    checkpointer = MemorySaver()

    if use_interrupt_before:
        # ── Strategy 1: Declarative interrupt ────────────────────────────
        # Graph always pauses before 'sensitive_tools' node
        return g.compile(
            checkpointer=checkpointer,
            interrupt_before=["sensitive_tools"]
        )
    else:
        # ── Strategy 2: Programmatic interrupt (NodeInterrupt) ───────────
        # sensitive_check_node raises NodeInterrupt conditionally
        return g.compile(checkpointer=checkpointer)


# ── Run with HITL ──────────────────────────────────────────────────────────────

def run_with_hitl(task: str, thread_id: str = "thread-1", auto_approve: bool = False):
    """
    Demonstrates the full HITL cycle:
      1. Start graph run
      2. Graph pauses at sensitive tool
      3. Human reviews and decides
      4. Resume with decision
    """
    app = build_hitl_graph(use_interrupt_before=True)
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\nTask: {task}")

    # ── Phase 1: Run until first interrupt ───────────────────────────────
    initial_input = {
        "messages":        [HumanMessage(content=task)],
        "human_feedback":  "",
        "requires_approval": False,
    }

    result = app.invoke(initial_input, config)

    # Check if graph paused (has pending interrupts)
    state = app.get_state(config)

    if state.next:
        print(f"\n  [PAUSED] Graph stopped before node(s): {state.next}")
        last_msg = state.values["messages"][-1]

        # Show human what the agent wants to do
        print(f"\n{'═'*60}")
        print(f"  ⚠️  HUMAN APPROVAL REQUIRED")
        print(f"{'═'*60}")
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                print(f"  Tool : {tc['name']}")
                print(f"  Args : {json.dumps(tc['args'], indent=2)}")
        print(f"{'═'*60}")

        if not auto_approve:
            choice = input("  Approve? [y/n]: ").strip().lower()
            approved = choice == "y"
        else:
            approved = True
            print("  [Auto-approved]")

        # ── Phase 2: Resume based on human decision ───────────────────────
        if approved:
            print(f"  [HITL] ✓ Resuming graph...")
            # Resume: invoke with None (uses checkpoint) — continues from pause
            final = app.invoke(None, config)
        else:
            print(f"  [HITL] ✗ Injecting rejection into state...")
            # Inject human rejection into state, then resume
            app.update_state(config, {
                "human_feedback": "The human rejected this action. Do not proceed with it."
            })
            final = app.invoke(None, config)

        last = final["messages"][-1]
        return last.content if hasattr(last, "content") else str(last)

    else:
        # No interrupt — graph completed normally
        last = result["messages"][-1]
        return last.content if hasattr(last, "content") else str(last)


# ── Demonstrate interrupt_after ────────────────────────────────────────────────

def run_with_interrupt_after(task: str):
    """
    interrupt_after: pause AFTER a node runs so human can review its output.
    Classic "review before continuing" pattern.
    """
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(safe_tools))
    g.add_conditional_edges("agent", lambda s: "tools"
        if (hasattr(s["messages"][-1], "tool_calls") and s["messages"][-1].tool_calls)
        else END, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    g.set_entry_point("agent")

    # Pause AFTER agent runs — review its plan before executing tools
    app = g.compile(
        checkpointer=MemorySaver(),
        interrupt_after=["agent"]          # ← pause after agent node
    )

    config = {"configurable": {"thread_id": "after-demo"}}
    app.invoke({"messages": [HumanMessage(content=task)], "human_feedback": "", "requires_approval": False}, config)

    state = app.get_state(config)
    if state.next:
        last = state.values["messages"][-1]
        print(f"\n  [interrupt_after=agent] Agent says: {getattr(last, 'content', '')[:200]}")
        print(f"  Next node would be: {state.next}")
        print(f"  Human can now: review, modify state, or resume.")

        # Auto-resume for demo
        final = app.invoke(None, config)
        return final["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph", "10 — Human-in-the-Loop", OPENAI_MODEL)

    print("\n── Strategy 1: interrupt_before (declarative) ──")
    r1 = run_with_hitl(
        "Get NVIDIA stock price, then email a summary to invest@fund.com",
        thread_id="demo-1",
        auto_approve=True,
    )
    print(f"\nFinal: {r1[:300]}")

    print("\n\n── Strategy 2: interrupt_after (review output before continuing) ──")
    r2 = run_with_interrupt_after("What is the weather in Tokyo and London?")
    if r2:
        print(f"\nFinal: {r2[:300]}")

    print("\n── LANGGRAPH HITL IS THE GOLD STANDARD ──")
    print("interrupt_before=[node]  → declarative pause, zero code in node")
    print("interrupt_after=[node]   → review output before continuing")
    print("NodeInterrupt(msg)       → conditional pause from inside a node")
    print("app.invoke(None, config) → resume from exact checkpoint")
    print("app.update_state(config) → inject human correction into state")
    print("MemorySaver/SqliteSaver  → pause survives server restarts")
    print("get_state_history()      → full audit trail of every pause")
    print()
    print("This is the ONLY SDK where a paused workflow can survive:")
    print("  - Server restarts")
    print("  - Hours or days of wait time")
    print("  - Multiple reviewers across different sessions")
