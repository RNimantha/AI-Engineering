"""
UC09 — Supervisor | Claude Agent SDK
═════════════════════════════════════
Agent SDK supervisor: parent agent classifies task, spawns child specialists.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def quick_query(prompt: str, system: str = "", tools=None) -> str:
    text = ""
    async for event in claude_agent_sdk.query(
        prompt=prompt,
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL, max_turns=5,
            system_prompt=system or "You are a helpful assistant.",
            allowed_tools=tools or [],
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    text = block.text
    return text


async def supervisor_route(task: str) -> str:
    """Route the task to the right specialist."""
    route = await quick_query(
        f"Classify: '{task}'. Reply ONLY: MATH, RESEARCH, WRITER, or DATA",
        system="You are a router. One word answer only."
    )
    return route.strip().upper().split()[0]  # take first word


async def run_supervisor(task: str) -> str:
    route = await supervisor_route(task)
    print(f"  [Supervisor → {route}]")

    if route == "MATH":
        return await quick_query(
            task + "\nUse Python via Bash for calculations.",
            system="You are a math expert.",
            tools=["Bash"]
        )
    elif route == "RESEARCH":
        return await quick_query(
            task, system="You are a research specialist. Be factual.",
            tools=["Bash"]
        )
    elif route == "DATA":
        return await quick_query(
            task + "\nUse Python to compute/fetch the data via Bash.",
            system="You are a data specialist.",
            tools=["Bash"]
        )
    else:  # WRITER
        return await quick_query(task, system="You are an expert writer.")


async def main():
    header("Claude Agent SDK", "09 — Supervisor", ANTHROPIC_MODEL)
    tasks = [
        "What is 15% compound growth on $50,000 over 5 years?",
        "What is the current AI chip market situation for NVIDIA?",
        "Write a 3-sentence summary of why AI is transforming finance.",
        "Calculate: if NVDA is at $875, what is 12% growth over 2 years?",
    ]
    for task in tasks:
        print(f"\nTask: {task}")
        result = await run_supervisor(task)
        print(f"Answer: {result[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
