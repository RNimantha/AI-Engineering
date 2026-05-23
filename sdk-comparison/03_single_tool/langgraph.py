"""
UC03 — Single Tool | LangGraph
════════════════════════════════
KEY INSIGHT — Tool use with LangGraph:
  LangGraph abstracts the agentic loop into a graph structure.
  Instead of writing while True + stop_reason checks, you:
    1. Define tools with @tool decorator (LangChain)
    2. Create a ToolNode that executes them
    3. Wire: llm_node → (conditional) → tool_node → llm_node (cycle!)
    4. The graph CYCLES automatically until the LLM stops calling tools

  This is the standard LangGraph "ReAct agent" pattern.
  The cycle is: agent_node → tool_node → agent_node → ... → END

  prebuilt.create_react_agent() gives you this whole pattern in one line.
  Building it manually teaches you what's happening inside.

  KEY ADVANTAGE over manual loop:
    The conditional edge logic (should_continue) is reusable across
    any graph — you don't rewrite it per agent.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
import operator
import math

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── Step 1: Define tool with LangChain @tool decorator ──────────────────────
# LangChain reads the docstring and type hints to build the schema automatically
# No manual JSON schema needed — this is the biggest convenience vs raw SDKs

@tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Supports: +, -, *, /, **, sqrt, log, sin, cos, pi.
    Example: 'sqrt(144)' or '10000 * (1.07 ** 20)'
    """
    import re
    try:
        expr = expression.lower().replace("^", "**")
        expr = expr.replace("sqrt(", "math.sqrt(")
        expr = expr.replace("log(", "math.log(")
        expr = expr.replace("pi", str(math.pi))
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 6)}"
    except Exception as e:
        return f"Error: {e}"


# ── Step 2: Define State ─────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


# ── Step 3: Define Nodes ─────────────────────────────────────────────────────

tools = [calculate]
llm = ChatOpenAI(model=OPENAI_MODEL).bind_tools(tools)   # bind_tools attaches schema


def agent_node(state: AgentState) -> dict:
    """Call the LLM. Returns text OR a tool_call."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """
    Conditional edge: decide where to go after the LLM responds.
    If last message has tool_calls → go to tools node
    Otherwise → END
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ── Step 4: Build Graph ──────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))   # ToolNode executes tools automatically

    graph.set_entry_point("agent")

    # Conditional edge: after agent, either call tools or end
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", END: END}
    )

    # After tools → always go back to agent (the cycle)
    graph.add_edge("tools", "agent")

    return graph.compile()


def run_with_tool(user_message: str) -> str:
    app = build_graph()
    print(f"\nUser: {user_message}")

    result = app.invoke({
        "messages": [
            SystemMessage(content="You are a helpful math assistant."),
            HumanMessage(content=user_message)
        ]
    })

    return result["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph", "03 — Single Tool (Calculator)", OPENAI_MODEL)

    print(run_with_tool("What is 1337 * 42?"))
    print(run_with_tool(
        "If I invest $10,000 at 7% annual return for 20 years, "
        "what will it be worth? Use 10000 * (1.07 ** 20)"
    ))
    print(run_with_tool("What is the hypotenuse of a 5-12 right triangle?"))

    print("\n── LANGGRAPH TOOL USE ADVANTAGES ──")
    print("1. @tool decorator: no manual JSON schema — LangChain reads type hints")
    print("2. ToolNode: no manual tool dispatch — it calls the function for you")
    print("3. should_continue: reusable across all agents in your system")
    print("4. Graph cycle: replace while True loop with add_edge('tools','agent')")
    print()
    print("── ONE-LINER OPTION (prebuilt) ──")
    print("from langgraph.prebuilt import create_react_agent")
    print("app = create_react_agent(llm, tools=[calculate])")
    print("→ Same graph, zero boilerplate — use for quick prototyping")
