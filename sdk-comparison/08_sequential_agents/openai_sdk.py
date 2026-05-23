"""
UC08 — Sequential Agents | OpenAI SDK
Same pipeline, OpenAI syntax. Identical concept.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()
OPENAI_MODEL = "gpt-4o-mini"


def run_agent(client, system: str, user: str, tools=None) -> str:
    messages = [{"role":"system","content":system}, {"role":"user","content":user}]
    while True:
        kwargs = dict(model=OPENAI_MODEL, max_tokens=1024, messages=messages)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        response = client.chat.completions.create(**kwargs)
        msg = response.choices[0].message
        finish = response.choices[0].finish_reason
        if finish == "stop":
            return msg.content
        if finish == "tool_calls":
            messages.append(msg)
            for tc in msg.tool_calls:
                result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
                messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
        else:
            break
    return ""


def run_pipeline(topic: str) -> str:
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    search_tools = [t for t in OPENAI_TOOLS if t["function"]["name"] in ("search_web","get_stock_price")]
    calc_tools   = [t for t in OPENAI_TOOLS if t["function"]["name"] == "calculate"]

    print(f"\n{'━'*60}\nPipeline: {topic}\n{'━'*60}")

    print("  [Agent 1: Researcher]")
    research = run_agent(client,
        "You are a research analyst. Gather factual data. Use tools.",
        f"Research: {topic}", tools=search_tools)

    print("  [Agent 2: Analyst]")
    analysis = run_agent(client,
        "You are a financial analyst. Compute metrics. Use calculate tool.",
        f"Analyse:\n{research}", tools=calc_tools)

    print("  [Agent 3: Writer]")
    report = run_agent(client,
        "You are a business writer. Write a professional report.",
        f"Write report from:\n{analysis}")

    return report


if __name__ == "__main__":
    header("OpenAI Python SDK", "08 — Sequential Agents", OPENAI_MODEL)
    report = run_pipeline(
        "NVIDIA stock: current price, AI outlook, 3-year return at 25% growth"
    )
    print(f"\nFINAL REPORT:\n{'─'*60}\n{report}")
    print("\n── DIFF FROM CLAUDE SDK ──")
    print("Structurally identical pipeline — just OpenAI syntax throughout")
    print("Swap anthropic.Anthropic() → OpenAI(), adjust response access patterns")
