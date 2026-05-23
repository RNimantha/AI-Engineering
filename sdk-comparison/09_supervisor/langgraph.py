"""
UC09 — Supervisor | LangGraph
═══════════════════════════════
KEY INSIGHT — LangGraph supervisor is its strongest use case:
  The supervisor pattern maps PERFECTLY to LangGraph's conditional edges.
  The router node returns a routing decision → conditional edge picks the node.

  supervisor_node → conditional_edge → math_node
                                     → research_node
                                     → writer_node
                                     → data_node
                                     → END

  Each specialist runs, then routes BACK to supervisor for next task
  (if the supervisor decides more work is needed) or to END.

  This is LangGraph's canonical multi-agent pattern.
  create_react_agent() per specialist + supervisor graph is the
  production-grade pattern used in real enterprise deployments.
"""

import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def calculate(expression: str) -> str:
    """Evaluate math expression."""
    try:
        expr = expression.lower().replace("^","**").replace("sqrt(","math.sqrt(")
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 4)}"
    except Exception as e:
        return f"Error: {e}"

@tool
def search_web(query: str) -> str:
    """Search the web."""
    from shared.tools import search_web as _s; import json as j
    return j.dumps(_s(query)[:2])

@tool
def get_stock_price(ticker: str) -> str:
    """Get stock price."""
    from shared.tools import get_stock_price as _g; import json as j
    return j.dumps(_g(ticker))

@tool
def get_weather(city: str) -> str:
    """Get weather."""
    from shared.tools import get_weather as _w; import json as j
    return j.dumps(_w(city))


# ── State ─────────────────────────────────────────────────────────────────────

class SupervisorState(TypedDict):
    messages:  Annotated[list, operator.add]
    next_agent: str          # supervisor's routing decision
    task:       str          # original task


# ── Specialist agents as LangGraph subgraphs ─────────────────────────────────
# create_react_agent gives each specialist its own full ReAct loop

math_agent     = create_react_agent(ChatOpenAI(model=OPENAI_MODEL), tools=[calculate])
research_agent = create_react_agent(ChatOpenAI(model=OPENAI_MODEL), tools=[search_web, get_stock_price])
writer_agent   = create_react_agent(ChatOpenAI(model=OPENAI_MODEL), tools=[])
data_agent     = create_react_agent(ChatOpenAI(model=OPENAI_MODEL), tools=[get_stock_price, get_weather])


def make_specialist_node(agent, system_msg: str):
    """Wrap a specialist agent as a supervisor graph node."""
    def node(state: SupervisorState) -> dict:
        result = agent.invoke({
            "messages": [SystemMessage(content=system_msg)] + state["messages"]
        })
        return {"messages": [result["messages"][-1]], "next_agent": "DONE"}
    return node


# ── Supervisor node ───────────────────────────────────────────────────────────

def supervisor_node(state: SupervisorState) -> dict:
    """LLM-based router — classifies task and picks specialist."""
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    response = llm.invoke([
        SystemMessage(content=(
            "Route the user task. Reply ONLY with one of: MATH, RESEARCH, WRITER, DATA, DONE\n"
            "DONE = task already answered and we should stop."
        )),
        HumanMessage(content=state["task"])
    ])
    decision = response.content.strip().upper().split()[0]
    print(f"  [Supervisor] → {decision}")
    return {"next_agent": decision}


def route_decision(state: SupervisorState) -> str:
    """Conditional edge: read next_agent from state."""
    return state.get("next_agent", "DONE")


# ── Build supervisor graph ────────────────────────────────────────────────────

def build_supervisor_graph():
    g = StateGraph(SupervisorState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("math",       make_specialist_node(math_agent,     "You are a math expert."))
    g.add_node("research",   make_specialist_node(research_agent, "You are a research specialist."))
    g.add_node("writer",     make_specialist_node(writer_agent,   "You are an expert writer."))
    g.add_node("data",       make_specialist_node(data_agent,     "You are a data specialist."))

    g.set_entry_point("supervisor")

    # Supervisor routes to any specialist, or END if done
    g.add_conditional_edges("supervisor", route_decision, {
        "MATH":     "math",
        "RESEARCH": "research",
        "WRITER":   "writer",
        "DATA":     "data",
        "DONE":     END,
    })

    # After each specialist, route back to supervisor (for multi-step tasks)
    for specialist in ["math", "research", "writer", "data"]:
        g.add_edge(specialist, "supervisor")   # ← CYCLE back to supervisor!

    return g.compile()


def run_supervisor(task: str) -> str:
    app = build_supervisor_graph()
    print(f"\nTask: {task}")
    result = app.invoke({
        "messages":   [HumanMessage(content=task)],
        "next_agent": "",
        "task":       task,
    })
    return result["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph", "09 — Supervisor", OPENAI_MODEL)

    tasks = [
        "What is 15% compound growth on $50,000 over 5 years?",
        "What is NVIDIA's stock price?",
        "Write a 3-sentence summary of why AI is transforming finance.",
        "What is the weather in Tokyo?",
    ]
    for task in tasks:
        result = run_supervisor(task)
        print(f"Answer: {result[:200]}\n")

    print("\n── LANGGRAPH SUPERVISOR IS THE GOLD STANDARD ──")
    print("Each specialist = create_react_agent() — full ReAct loop per specialist")
    print("Routing = conditional edges — declarative, auditable")
    print("Cycle back to supervisor = multi-step tasks handled naturally")
    print("Add checkpointer → entire multi-agent run is resumable")
    print("Add streaming → watch routing decisions as they happen")
    print()
    print("This is THE pattern for production multi-agent systems.")
