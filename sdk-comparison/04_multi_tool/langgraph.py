"""
UC04 — Multi-Tool | LangGraph
══════════════════════════════
KEY INSIGHT — LangGraph multi-tool:
  Adding more tools to LangGraph requires ZERO change to the graph structure.
  You just add tools to the list — the ToolNode handles dispatch automatically.

  New concept: create_react_agent() prebuilt
    This is the one-liner that gives you the full ReAct graph
    (agent → conditional → tools → agent cycle) without building it manually.
    Use it for quick prototyping, build manually when you need custom nodes.

  Also shown: how to observe which tools were called via stream_mode="updates"
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── All 5 tools as LangChain @tool functions ─────────────────────────────────
# Docstrings become the tool descriptions — write them clearly!

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression. Supports +,-,*,/,**,sqrt,log,pi."""
    try:
        expr = expression.lower().replace("^", "**")
        expr = expr.replace("sqrt(", "math.sqrt(").replace("log(", "math.log(")
        expr = expr.replace("pi", str(math.pi))
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 6)}"
    except Exception as e:
        return f"Error: {e}"

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city (London, Tokyo, New York, Paris, Dubai, etc.)."""
    from shared.tools import get_weather as _get_weather
    import json
    return json.dumps(_get_weather(city))

@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic."""
    from shared.tools import search_web as _search_web
    import json
    results = _search_web(query)
    return json.dumps(results[:2])  # top 2 results

@tool
def get_stock_price(ticker: str) -> str:
    """Get current stock price for a ticker (AAPL, MSFT, NVDA, TSLA, etc.)."""
    from shared.tools import get_stock_price as _get_stock
    import json
    return json.dumps(_get_stock(ticker))

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    from shared.tools import send_email as _send
    import json
    return json.dumps(_send(to, subject, body))


all_tools = [calculate, get_weather, search_web, get_stock_price, send_email]


# ── Approach 1: create_react_agent (prebuilt one-liner) ─────────────────────

def run_prebuilt(user_message: str) -> str:
    """Fastest way to get a multi-tool agent running."""
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    app = create_react_agent(llm, tools=all_tools)

    result = app.invoke({
        "messages": [HumanMessage(content=user_message)]
    })
    return result["messages"][-1].content


# ── Approach 2: Manual graph with streaming visibility ────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

def run_with_visibility(user_message: str):
    """Manual graph so we can observe each node's contribution."""
    llm = ChatOpenAI(model=OPENAI_MODEL).bind_tools(all_tools)

    def agent_node(state):
        msgs = [SystemMessage(content="You are a helpful assistant.")] + state["messages"]
        return {"messages": [llm.invoke(msgs)]}

    def should_continue(state):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(all_tools))
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    app = g.compile()

    print(f"\nUser: {user_message}")
    # stream updates to see each node's output
    for node_name, update in app.stream(
        {"messages": [HumanMessage(content=user_message)]},
        stream_mode="updates"
    ):
        if node_name == "tools":
            for msg in update.get("messages", []):
                if hasattr(msg, "content"):
                    print(f"  [Tool result from '{msg.name}']: {str(msg.content)[:80]}")
        elif node_name == "agent":
            last = update.get("messages", [])
            if last and hasattr(last[-1], "content") and last[-1].content:
                print(f"  [Agent response]: {last[-1].content[:100]}")

    result = app.invoke({"messages": [HumanMessage(content=user_message)]})
    return result["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph", "04 — Multi-Tool", OPENAI_MODEL)

    print("=== Prebuilt create_react_agent (one-liner) ===")
    result = run_prebuilt(
        "What is the weather in London? Also calculate 1337 * 42."
    )
    print(f"Answer: {result}")

    print("\n=== Manual graph with stream visibility ===")
    result2 = run_with_visibility(
        "Compare AAPL and NVDA stock prices. Which has better today's performance?"
    )
    print(f"\nFinal: {result2}")

    print("\n── LANGGRAPH MULTI-TOOL SUMMARY ──")
    print("create_react_agent(llm, tools=[...]) = full agent in 1 line")
    print("Manual graph = same behaviour + full observability via streaming")
    print("Adding new tools = just append to tools list, zero graph changes")
