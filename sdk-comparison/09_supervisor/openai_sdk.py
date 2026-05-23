"""
UC09 — Supervisor | OpenAI SDK
Same pattern. OpenAI syntax.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.tools import OPENAI_TOOLS, execute_tool
from shared.utils import load_env, header, require_key

load_env()
OPENAI_MODEL = "gpt-4o-mini"

SUPERVISOR_PROMPT = """Route the request. Reply ONLY with: MATH, RESEARCH, WRITER, or DATA."""


def supervisor(client, msg: str) -> str:
    r = client.chat.completions.create(
        model=OPENAI_MODEL, max_tokens=5,
        messages=[{"role":"system","content":SUPERVISOR_PROMPT},{"role":"user","content":msg}]
    )
    return r.choices[0].message.content.strip().upper()


def run_agent(client, system, user, tool_names=None):
    tools = [t for t in OPENAI_TOOLS if t["function"]["name"] in (tool_names or [])]
    msgs = [{"role":"system","content":system},{"role":"user","content":user}]
    while True:
        kwargs = dict(model=OPENAI_MODEL, max_tokens=1024, messages=msgs)
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        r = client.chat.completions.create(**kwargs)
        m = r.choices[0].message
        if r.choices[0].finish_reason == "stop":
            return m.content
        if r.choices[0].finish_reason == "tool_calls":
            msgs.append(m)
            for tc in m.tool_calls:
                result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
                msgs.append({"role":"tool","tool_call_id":tc.id,"content":result})
        else: break
    return ""


SPECIALISTS = {
    "MATH":     lambda c,t: run_agent(c,"Math expert. Use calculate.","T: "+t,["calculate"]),
    "RESEARCH": lambda c,t: run_agent(c,"Research specialist.","T: "+t,["search_web","get_stock_price"]),
    "WRITER":   lambda c,t: run_agent(c,"Expert writer. Be clear.","T: "+t),
    "DATA":     lambda c,t: run_agent(c,"Data specialist.","T: "+t,["get_stock_price","get_weather"]),
}


def run_supervisor(task: str) -> str:
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    route = supervisor(client, task)
    print(f"  [Supervisor → {route}]")
    return SPECIALISTS.get(route, SPECIALISTS["WRITER"])(client, task)


if __name__ == "__main__":
    header("OpenAI Python SDK", "09 — Supervisor", OPENAI_MODEL)
    tasks = [
        "What is 15% compound growth on $50,000 over 5 years?",
        "What is NVIDIA's current stock price?",
        "Write a 3-sentence summary of why AI is transforming finance.",
        "What is the weather in Tokyo?",
    ]
    for task in tasks:
        print(f"\nTask: {task}")
        print(f"Answer: {run_supervisor(task)[:200]}")
