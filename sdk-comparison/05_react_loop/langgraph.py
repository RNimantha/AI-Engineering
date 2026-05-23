"""
UC05 — ReAct Loop | LangGraph
══════════════════════════════
KEY INSIGHT — LangGraph ReAct with EXTENDED STATE:
  The prebuilt create_react_agent IS a ReAct loop.
  But LangGraph lets you add custom state fields that persist across turns.

  In UC03/UC04 our state only had messages[].
  In a real ReAct agent you want to track:
    - reasoning_steps: list of "what did I decide to do and why"
    - tool_calls_made:  count of tool invocations (for cost tracking)
    - intermediate_findings: key facts gathered so far

  LangGraph makes this trivial via the state TypedDict.
  No other SDK lets you transparently persist custom data between iterations.

  Also shown: how to add a BEFORE/AFTER hook node to an existing graph
  (inject logging, validation, or side-effects without changing agent logic)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── Extended state — custom fields beyond messages ───────────────────────────

class ReactState(TypedDict):
    messages:     Annotated[list, operator.add]   # full message history
    tool_calls_made: int                          # custom: count tool invocations
    reasoning_log:   Annotated[list, operator.add]  # custom: per-step reasoning


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        expr = expression.lower().replace("^","**").replace("sqrt(","math.sqrt(")
        expr = expr.replace("pi", str(math.pi))
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 4)}"
    except Exception as e:
        return f"Error: {e}"

@tool
def get_stock_price(ticker: str) -> str:
    """Get stock price for AAPL, MSFT, NVDA, TSLA, GOOGL, META, AMZN."""
    from shared.tools import get_stock_price as _get
    import json
    return json.dumps(_get(ticker))

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    from shared.tools import search_web as _search
    import json
    return json.dumps(_search(query)[:1])

tools = [calculate, get_stock_price, search_web]
llm = ChatOpenAI(model=OPENAI_MODEL).bind_tools(tools)


# ── Nodes with extended state ─────────────────────────────────────────────────

def agent_node(state: ReactState) -> dict:
    """LLM reasoning node — also logs its decision."""
    msgs = [SystemMessage(content=(
        "You are a research assistant. Think step by step. "
        "Use tools to gather data before making conclusions."
    ))] + state["messages"]

    response = llm.invoke(msgs)

    # Log what the agent is doing (custom state field)
    reasoning = ""
    if hasattr(response, "tool_calls") and response.tool_calls:
        tools_planned = [tc.get("name","?") if isinstance(tc,dict) else tc.name
                         for tc in response.tool_calls]
        reasoning = f"Planning to call: {tools_planned}"
    elif response.content:
        reasoning = f"Final synthesis: {response.content[:80]}..."

    return {
        "messages": [response],
        "reasoning_log": [reasoning] if reasoning else [],
        "tool_calls_made": 0,  # will be incremented in tool_tracker_node
    }


def tool_tracker_node(state: ReactState) -> dict:
    """
    BEFORE tool execution: count how many tools are being called this turn.
    This is a custom node injected between agent and tools.
    No other SDK allows this cleanly.
    """
    last_msg = state["messages"][-1]
    call_count = len(last_msg.tool_calls) if hasattr(last_msg, "tool_calls") else 0
    print(f"  [Tracker] About to execute {call_count} tool call(s). "
          f"Total so far: {state['tool_calls_made']}")
    return {"tool_calls_made": state["tool_calls_made"] + call_count}


def should_continue(state: ReactState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tracker"   # go to tracker THEN tools
    return END


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(ReactState)

    g.add_node("agent",   agent_node)
    g.add_node("tracker", tool_tracker_node)   # custom between-step node
    g.add_node("tools",   ToolNode(tools))

    g.set_entry_point("agent")
    g.add_conditional_edges("agent", should_continue, {"tracker": "tracker", END: END})
    g.add_edge("tracker", "tools")   # tracker → tools (always)
    g.add_edge("tools",   "agent")   # tools → agent (cycle)

    return g.compile()


def run_react(user_message: str) -> str:
    app = build_graph()

    print(f"\n{'━'*60}")
    print(f"Task: {user_message}")
    print(f"{'━'*60}")

    final_state = app.invoke({
        "messages":        [HumanMessage(content=user_message)],
        "tool_calls_made": 0,
        "reasoning_log":   [],
    })

    print(f"\n[Total tool calls made: {final_state['tool_calls_made']}]")
    print(f"[Reasoning log: {final_state['reasoning_log']}]")

    return final_state["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph", "05 — ReAct Loop", OPENAI_MODEL)

    result = run_react(
        "I want to invest $10,000. "
        "Check AAPL and NVDA stock prices, search 'best tech stocks 2025'. "
        "Then calculate: AAPL at 15% growth for 3 years (10000*1.15**3) "
        "vs NVDA at 25% growth (10000*1.25**3). "
        "Which is the better investment and why?"
    )
    print(f"\nFINAL ANSWER:\n{result}")

    print("\n── LANGGRAPH ReAct UNIQUE FEATURE ──")
    print("Custom state fields (tool_calls_made, reasoning_log) persist across ALL turns")
    print("Custom 'tracker' node injected BETWEEN agent and tools")
    print("No other SDK lets you do this without rewriting the loop")
    print()
    print("This is why LangGraph is preferred for production agents:")
    print("You get observability, auditability, and control over every step.")
