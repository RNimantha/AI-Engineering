"""
UC09 — Supervisor / Orchestrator | Claude SDK
══════════════════════════════════════════════
KEY INSIGHT — Supervisor pattern:
  One ROUTER agent classifies the task and dispatches to specialist agents.
  This is the foundation of production AI systems:
    "Math question?"   → Math Agent
    "Research needed?" → Research Agent
    "Write something?" → Writer Agent
    "Need data?"       → Data Agent

  The supervisor doesn't do the work — it ROUTES to who can.
  Specialists don't route — they just execute their one task perfectly.

  This is fundamentally different from UC08 (sequential):
    Sequential: A always → B always → C always (fixed pipeline)
    Supervisor: Router decides which specialist to call (dynamic routing)

  The supervisor uses Claude's reasoning to classify intent,
  not regex or keyword matching — making it robust to varied phrasing.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ── Supervisor decides which specialist to call ───────────────────────────────

SUPERVISOR_PROMPT = """You are a task router. Classify the user's request and route it.

Available specialists:
  MATH     → calculations, formulas, numerical problems
  RESEARCH → facts, news, market data, web search
  WRITER   → reports, summaries, explanations, creative text
  DATA     → stock prices, financial data, specific numbers

Respond with ONLY one word: MATH, RESEARCH, WRITER, or DATA.
No explanation. Just the routing decision.
"""

def supervisor(client, user_message: str) -> str:
    """Returns the specialist name to route to."""
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=10,
        system=SUPERVISOR_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text.strip().upper()


# ── Specialist agents ─────────────────────────────────────────────────────────

def math_agent(client, task: str) -> str:
    calc_tool = [t for t in ANTHROPIC_TOOLS if t["name"] == "calculate"]
    messages = [{"role": "user", "content": task}]
    while True:
        r = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=512,
            system="You are a math expert. Use calculate tool. Show your work.",
            tools=calc_tool, messages=messages
        )
        if r.stop_reason == "end_turn":
            return next((b.text for b in r.content if hasattr(b,"text")), "")
        if r.stop_reason == "tool_use":
            messages.append({"role":"assistant","content":r.content})
            results = [{"type":"tool_result","tool_use_id":b.id,
                        "content":execute_tool(b.name,b.input)}
                       for b in r.content if b.type=="tool_use"]
            messages.append({"role":"user","content":results})
        else: break
    return ""


def research_agent(client, task: str) -> str:
    tools = [t for t in ANTHROPIC_TOOLS if t["name"] in ("search_web","get_stock_price")]
    messages = [{"role": "user", "content": task}]
    while True:
        r = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=1024,
            system="You are a research specialist. Use search and data tools.",
            tools=tools, messages=messages
        )
        if r.stop_reason == "end_turn":
            return next((b.text for b in r.content if hasattr(b,"text")), "")
        if r.stop_reason == "tool_use":
            messages.append({"role":"assistant","content":r.content})
            results = [{"type":"tool_result","tool_use_id":b.id,
                        "content":execute_tool(b.name,b.input)}
                       for b in r.content if b.type=="tool_use"]
            messages.append({"role":"user","content":results})
        else: break
    return ""


def writer_agent(client, task: str) -> str:
    r = client.messages.create(
        model=ANTHROPIC_MODEL, max_tokens=1024,
        system="You are an expert writer. Write clearly, concisely, professionally.",
        messages=[{"role": "user", "content": task}]
    )
    return r.content[0].text


def data_agent(client, task: str) -> str:
    tools = [t for t in ANTHROPIC_TOOLS if t["name"] in ("get_stock_price","get_weather")]
    messages = [{"role": "user", "content": task}]
    while True:
        r = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=512,
            system="You are a data retrieval specialist. Fetch exact requested data.",
            tools=tools, messages=messages
        )
        if r.stop_reason == "end_turn":
            return next((b.text for b in r.content if hasattr(b,"text")), "")
        if r.stop_reason == "tool_use":
            messages.append({"role":"assistant","content":r.content})
            results = [{"type":"tool_result","tool_use_id":b.id,
                        "content":execute_tool(b.name,b.input)}
                       for b in r.content if b.type=="tool_use"]
            messages.append({"role":"user","content":results})
        else: break
    return ""


# ── Orchestrator: routes + dispatches ────────────────────────────────────────

SPECIALIST_MAP = {
    "MATH":     math_agent,
    "RESEARCH": research_agent,
    "WRITER":   writer_agent,
    "DATA":     data_agent,
}

def run_supervisor(user_message: str) -> str:
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    routing = supervisor(client, user_message)
    print(f"  [Supervisor] Routing '{user_message[:50]}...' → {routing}")
    agent_fn = SPECIALIST_MAP.get(routing, writer_agent)
    result = agent_fn(client, user_message)
    return result


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "09 — Supervisor / Orchestrator", ANTHROPIC_MODEL)

    tasks = [
        "What is 15% compound annual growth on $50,000 over 5 years?",
        "What is the current NVIDIA stock price and recent market sentiment?",
        "Write a 3-sentence executive summary of why AI is transforming finance.",
        "What is the weather in Tokyo right now?",
    ]

    for task in tasks:
        print(f"\nTask: {task}")
        result = run_supervisor(task)
        print(f"Answer: {result[:200]}")

    print("\n── SUPERVISOR PATTERN INSIGHT ──")
    print("Supervisor = LLM as a ROUTER (not a worker)")
    print("Specialists = narrow, deep expertise")
    print("Benefits: each specialist can be fine-tuned independently")
    print("          specialists can run in parallel (if tasks are independent)")
    print("          easy to add new specialists without changing existing ones")
