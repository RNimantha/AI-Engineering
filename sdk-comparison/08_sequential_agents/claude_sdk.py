"""
UC08 — Sequential Agents | Claude SDK (anthropic)
══════════════════════════════════════════════════
KEY INSIGHT — Multi-agent pipelines:
  Multiple agents, each with a distinct role, passing output as input.
  This is the pattern we built in the Clinical Trial Matcher:
    Anonymizer → Searcher → Evaluator → Scribe

  Each agent:
    - Has its own system prompt (specialized persona)
    - Receives the PREVIOUS agent's output as input
    - Produces a structured output for the NEXT agent

  Why multiple agents instead of one big prompt?
    1. Specialization: each agent can be tuned for one task
    2. Debuggability: you can test/swap individual agents
    3. Context window management: each agent has a lean context
    4. Parallelism potential: some agents can run in parallel (UC09)

  Pipeline: Researcher → Analyst → Writer
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.tools import ANTHROPIC_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"


def run_agent(client, system: str, user: str, tools=None, max_turns: int = 5) -> str:
    """Generic single-agent runner (reusable across all 3 agents)."""
    messages = [{"role": "user", "content": user}]
    while True:
        kwargs = dict(model=ANTHROPIC_MODEL, max_tokens=1024, system=system, messages=messages)
        if tools:
            kwargs["tools"] = tools
        response = client.messages.create(**kwargs)
        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if hasattr(b, "text")), "")
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    results.append({"type":"tool_result","tool_use_id":block.id,"content":result})
            messages.append({"role": "user", "content": results})
        else:
            break
    return ""


def research_agent(client, topic: str) -> str:
    """Agent 1: Researches a topic using search + stock tools."""
    print("  [Agent 1: Researcher] Gathering data...")
    search_tools = [t for t in ANTHROPIC_TOOLS if t["name"] in ("search_web", "get_stock_price")]
    return run_agent(
        client,
        system="You are a research analyst. Gather factual data on the given topic. "
               "Use search_web and get_stock_price tools. Summarize findings concisely.",
        user=f"Research this topic and gather all relevant data: {topic}",
        tools=search_tools,
    )


def analyst_agent(client, research_data: str) -> str:
    """Agent 2: Analyses the research and runs calculations."""
    print("  [Agent 2: Analyst] Analysing data...")
    calc_tools = [t for t in ANTHROPIC_TOOLS if t["name"] == "calculate"]
    return run_agent(
        client,
        system="You are a financial analyst. Given research data, perform calculations "
               "and provide a quantitative analysis. Use calculate tool for any math.",
        user=f"Analyse this research data and compute key metrics:\n\n{research_data}",
        tools=calc_tools,
    )


def writer_agent(client, analysis: str) -> str:
    """Agent 3: Writes the final report (no tools needed)."""
    print("  [Agent 3: Writer] Drafting report...")
    return run_agent(
        client,
        system="You are an expert business writer. Transform analysis into a clear, "
               "professional report. Use headers, bullet points, and plain English.",
        user=f"Write a professional investment report based on this analysis:\n\n{analysis}",
    )


def run_pipeline(topic: str) -> str:
    """Execute the 3-agent pipeline sequentially."""
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))

    print(f"\n{'━'*60}")
    print(f"Pipeline: {topic}")
    print(f"{'━'*60}")

    # Each agent's output feeds the next
    research  = research_agent(client, topic)
    analysis  = analyst_agent(client, research)
    report    = writer_agent(client, analysis)

    return report


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "08 — Sequential Agents", ANTHROPIC_MODEL)

    report = run_pipeline(
        "NVIDIA stock investment analysis — current price, AI market outlook, "
        "and potential return calculation if bought today and sold in 3 years at 25% annual growth"
    )
    print(f"\nFINAL REPORT:\n{'─'*60}\n{report}")

    print("\n── SEQUENTIAL AGENT KEY INSIGHT ──")
    print("Each agent has a NARROW, FOCUSED system prompt")
    print("Agent output = next agent input (simple string passing)")
    print("State lives in Python variables — no framework needed")
    print("This is the Clinical Trial Matcher pattern (Anonymizer→Searcher→Evaluator→Scribe)")
