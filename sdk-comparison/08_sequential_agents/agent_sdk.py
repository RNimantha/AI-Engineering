"""
UC08 — Sequential Agents | Claude Agent SDK
═════════════════════════════════════════════
KEY INSIGHT — Agent SDK subagents:
  The Agent SDK supports subagent architecture natively.
  A "parent" agent can spawn child agents and wait for their results.
  This is the Agent SDK's killer feature for complex multi-agent workflows.

  spawn_subagent() starts a child agent with its own context.
  The parent receives the child's result and continues.
  Nesting can be arbitrarily deep.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


async def run_single_agent(prompt: str, system: str, allowed_tools=None) -> str:
    """Run one agent turn and return its text output."""
    text = ""
    options = claude_agent_sdk.ClaudeCodeOptions(
        model=ANTHROPIC_MODEL,
        max_turns=5,
        system_prompt=system,
        allowed_tools=allowed_tools or [],
    )
    async for event in claude_agent_sdk.query(prompt=prompt, options=options):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text") and block.text:
                    text = block.text
    return text


async def run_pipeline(topic: str) -> str:
    """Three-agent pipeline using Agent SDK."""
    print(f"\n{'━'*60}\nPipeline: {topic}\n{'━'*60}")

    # Agent 1: Researcher (with Bash for web-like research)
    print("  [Agent 1: Researcher]")
    research = await run_single_agent(
        prompt=f"Research this topic thoroughly:\n{topic}\n"
               "Use Bash/Python to gather and organize facts. "
               "Output a structured summary of findings.",
        system="You are a research analyst. Gather factual, structured data.",
        allowed_tools=["Bash"],
    )
    print(f"  Research output: {research[:100]}...")

    # Agent 2: Analyst (uses research output)
    print("  [Agent 2: Analyst]")
    analysis = await run_single_agent(
        prompt=f"Perform quantitative analysis on this research:\n\n{research}\n\n"
               "Calculate key metrics using Python (Bash). Provide numbers.",
        system="You are a quantitative analyst. Compute metrics precisely.",
        allowed_tools=["Bash"],
    )
    print(f"  Analysis output: {analysis[:100]}...")

    # Agent 3: Writer (synthesizes into report)
    print("  [Agent 3: Writer]")
    report = await run_single_agent(
        prompt=f"Write a professional investment report from this analysis:\n\n{analysis}",
        system="You are a professional business writer. Write clearly and concisely.",
        allowed_tools=[],  # Writer doesn't need tools
    )

    return report


async def main():
    header("Claude Agent SDK", "08 — Sequential Agents", ANTHROPIC_MODEL)
    report = await run_pipeline(
        "NVIDIA (NVDA) stock investment: current market position, AI chip demand, "
        "3-year return projection at 25% annual growth"
    )
    print(f"\nFINAL REPORT:\n{'─'*60}\n{report}")

    print("\n── AGENT SDK SEQUENTIAL KEY POINTS ──")
    print("Each agent in Agent SDK = one claude_agent_sdk.query() call")
    print("Bash tool gives agents actual computation power (real Python execution)")
    print("No manual tool dispatch needed — SDK handles it")
    print("Agent SDK advantage: real code execution via Bash (not mocked tools)")


if __name__ == "__main__":
    asyncio.run(main())
