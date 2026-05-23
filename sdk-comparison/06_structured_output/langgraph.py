"""
UC06 — Structured Output | LangGraph
══════════════════════════════════════
KEY INSIGHT — LangGraph structured output:
  LangGraph's unique approach: a dedicated PARSER NODE in the graph.
  After the LLM generates text, a separate node validates/parses it.
  If parsing fails, the graph can RETRY automatically (loop back to LLM).

  This is the most robust structured output pattern:
    llm_node → parser_node → (success) → END
                           → (failure)  → llm_node (retry with error feedback)

  with_structured_output() wraps the LLM to return Pydantic objects.
  It's LangChain's version of OpenAI's beta.parse() — works with ANY LLM.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


class StockAnalysis(BaseModel):
    ticker: str
    company: str
    recommendation: str
    confidence: float
    key_reasons: list[str]
    target_price: Optional[float] = None
    risk_level: str


SAMPLE_TEXT = """
NVIDIA (NVDA) has been dominating the AI chip market.
Trading at $875.60 today (+12.4%).
Strong buy momentum driven by data center demand.
Some risk from China export restrictions.
Analysts consensus is bullish with targets of $950-1000.
"""


# ── Approach 1: with_structured_output() ─────────────────────────────────────
# One-liner: wraps the LLM to always return the Pydantic object

def extract_direct(text: str) -> StockAnalysis:
    """Simplest LangChain approach — no graph needed."""
    llm = ChatOpenAI(model=OPENAI_MODEL)
    structured_llm = llm.with_structured_output(StockAnalysis)
    return structured_llm.invoke([
        SystemMessage(content="You are a stock analyst. Be precise."),
        HumanMessage(content=f"Analyze:\n{text}")
    ])


# ── Approach 2: Graph with retry on parse failure ─────────────────────────────

class ParserState(TypedDict):
    messages:      Annotated[list, operator.add]
    parsed_output: Optional[StockAnalysis]
    parse_error:   str
    attempts:      int


def llm_node(state: ParserState) -> dict:
    """Generate analysis, with error feedback on retry."""
    llm = ChatOpenAI(model=OPENAI_MODEL)
    structured_llm = llm.with_structured_output(StockAnalysis)

    # On retry, add the error to messages
    msgs = [SystemMessage(content="You are a stock analyst.")] + state["messages"]
    if state["parse_error"]:
        msgs.append(HumanMessage(
            content=f"Previous attempt failed: {state['parse_error']}. Please try again carefully."
        ))

    try:
        result = structured_llm.invoke(msgs)
        return {
            "parsed_output": result,
            "parse_error":   "",
            "attempts":      state["attempts"] + 1,
        }
    except Exception as e:
        return {
            "parsed_output": None,
            "parse_error":   str(e),
            "attempts":      state["attempts"] + 1,
        }


def should_retry(state: ParserState) -> str:
    """Retry up to 3 times if parsing failed."""
    if state["parsed_output"] is not None:
        return "success"
    if state["attempts"] >= 3:
        return "give_up"
    return "retry"


def build_retry_graph():
    g = StateGraph(ParserState)
    g.add_node("llm", llm_node)
    g.set_entry_point("llm")
    g.add_conditional_edges("llm", should_retry, {
        "success":  END,
        "retry":    "llm",      # ← CYCLE: retry on failure
        "give_up":  END,
    })
    return g.compile()


def extract_with_retry(text: str) -> StockAnalysis:
    app = build_retry_graph()
    result = app.invoke({
        "messages":      [HumanMessage(content=f"Analyze:\n{text}")],
        "parsed_output": None,
        "parse_error":   "",
        "attempts":      0,
    })
    print(f"  [Attempts needed: {result['attempts']}]")
    return result["parsed_output"]


if __name__ == "__main__":
    header("LangGraph", "06 — Structured Output", OPENAI_MODEL)

    print("── Approach 1: with_structured_output() ──")
    result1 = extract_direct(SAMPLE_TEXT)
    print(f"Ticker:         {result1.ticker}")
    print(f"Recommendation: {result1.recommendation}")
    print(f"Confidence:     {result1.confidence:.0%}")
    print(f"Risk:           {result1.risk_level}")
    for r in result1.key_reasons:
        print(f"  • {r}")

    print("\n── Approach 2: Graph with retry logic ──")
    result2 = extract_with_retry(SAMPLE_TEXT)
    if result2:
        print(f"Result: {result2.ticker} → {result2.recommendation}")

    print("\n── STRUCTURED OUTPUT COMPARISON ──")
    print("OpenAI SDK:   client.beta.chat.completions.parse(response_format=Model)")
    print("Claude SDK:   tool_choice='tool' + Pydantic(**block.input)")
    print("LangGraph:    llm.with_structured_output(Model).invoke()")
    print("Agent SDK:    output_schema=Model in ClaudeCodeOptions")
    print()
    print("LangGraph UNIQUE: retry graph — automatically retries on parse failure")
    print("This is critical for production: LLMs occasionally generate malformed JSON")
