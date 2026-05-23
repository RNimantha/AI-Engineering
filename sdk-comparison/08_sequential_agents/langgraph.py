"""
UC08 — Sequential Agents | LangGraph
═══════════════════════════════════════
KEY INSIGHT — LangGraph sequential agents:
  In LangGraph, each agent IS a node. Sequential agents = linear edges.
  researcher_node → analyst_node → writer_node → END

  The massive advantage over Claude/OpenAI SDK manual chains:
    - State flows automatically (no manual variable passing)
    - You can inspect state between EVERY agent via streaming
    - Adding an agent = add a node + one edge
    - Removing an agent = remove a node + update edges
    - The state captures intermediate results for debugging

  Also shown: how to pass agent-specific context via state fields
  (not just passing text — passing structured data between agents)
"""

import sys, os, json, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


# ── Extended pipeline state ───────────────────────────────────────────────────

class PipelineState(TypedDict):
    topic:          str                                 # input
    research_data:  str                                 # Agent 1 output
    analysis_data:  str                                 # Agent 2 output
    final_report:   str                                 # Agent 3 output
    messages:       Annotated[list, operator.add]       # full message log


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """Search the web for information about a topic."""
    from shared.tools import search_web as _s
    return json.dumps(_s(query)[:2])

@tool
def get_stock_price(ticker: str) -> str:
    """Get stock price for a ticker symbol."""
    from shared.tools import get_stock_price as _g
    return json.dumps(_g(ticker))

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        expr = expression.lower().replace("^","**").replace("sqrt(","math.sqrt(")
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 4)}"
    except Exception as e:
        return f"Error: {e}"


# ── Agent nodes ───────────────────────────────────────────────────────────────

def researcher_node(state: PipelineState) -> dict:
    """Agent 1: Gathers data using search + stock tools."""
    llm = ChatOpenAI(model=OPENAI_MODEL).bind_tools([search_web, get_stock_price])
    msgs = [
        SystemMessage(content="You are a research analyst. Gather factual data. Use tools."),
        HumanMessage(content=f"Research: {state['topic']}")
    ]
    # Simple single-turn call (tool use handled inline for brevity)
    resp = llm.invoke(msgs)
    result_text = resp.content or f"Research on {state['topic']} gathered."
    print(f"  [Researcher] {result_text[:80]}...")
    return {
        "research_data": result_text,
        "messages": [HumanMessage(content=f"Research: {state['topic']}"), resp]
    }


def analyst_node(state: PipelineState) -> dict:
    """Agent 2: Analyses research and runs calculations."""
    llm = ChatOpenAI(model=OPENAI_MODEL).bind_tools([calculate])
    msgs = [
        SystemMessage(content="You are a quantitative analyst. Compute key metrics."),
        HumanMessage(content=f"Analyse this research:\n{state['research_data']}")
    ]
    resp = llm.invoke(msgs)
    result_text = resp.content or "Analysis complete."
    print(f"  [Analyst] {result_text[:80]}...")
    return {
        "analysis_data": result_text,
        "messages": [resp]
    }


def writer_node(state: PipelineState) -> dict:
    """Agent 3: Writes the final professional report."""
    llm = ChatOpenAI(model=OPENAI_MODEL)
    msgs = [
        SystemMessage(content="You are a professional business writer. Be clear and concise."),
        HumanMessage(content=f"Write a professional report from:\n{state['analysis_data']}")
    ]
    resp = llm.invoke(msgs)
    print(f"  [Writer] Report generated ({len(resp.content)} chars)")
    return {
        "final_report": resp.content,
        "messages": [resp]
    }


# ── Build sequential graph ────────────────────────────────────────────────────

def build_pipeline():
    g = StateGraph(PipelineState)

    g.add_node("researcher", researcher_node)
    g.add_node("analyst",    analyst_node)
    g.add_node("writer",     writer_node)

    # Linear pipeline: A → B → C → END
    g.set_entry_point("researcher")
    g.add_edge("researcher", "analyst")
    g.add_edge("analyst",    "writer")
    g.add_edge("writer",     END)

    return g.compile()


def run_pipeline(topic: str) -> str:
    app = build_pipeline()
    print(f"\n{'━'*60}\nPipeline: {topic}\n{'━'*60}")

    result = app.invoke({
        "topic":         topic,
        "research_data": "",
        "analysis_data": "",
        "final_report":  "",
        "messages":      [],
    })

    # All intermediate outputs are in state
    print(f"\n[Research data length:  {len(result['research_data'])} chars]")
    print(f"[Analysis data length:  {len(result['analysis_data'])} chars]")
    print(f"[Final report length:   {len(result['final_report'])} chars]")

    return result["final_report"]


if __name__ == "__main__":
    header("LangGraph", "08 — Sequential Agents", OPENAI_MODEL)

    report = run_pipeline(
        "NVIDIA (NVDA) investment analysis: current price, AI chip market, "
        "3-year return at 25% growth"
    )
    print(f"\nFINAL REPORT:\n{'─'*60}\n{report}")

    print("\n── LANGGRAPH SEQUENTIAL ADVANTAGES ──")
    print("State captures EVERY intermediate output (research, analysis, report)")
    print("Add streaming → see each agent's output as it completes")
    print("Add checkpointer → entire pipeline is resumable after crash")
    print("Swap a node → zero changes to rest of pipeline")
    print("Add conditional → skip analyst if research is too thin")
