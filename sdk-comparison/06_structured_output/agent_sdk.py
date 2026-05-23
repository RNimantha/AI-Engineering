"""
UC06 — Structured Output | Claude Agent SDK
════════════════════════════════════════════
KEY INSIGHT — Agent SDK Structured Outputs:
  The Agent SDK supports structured outputs via output_schema parameter.
  You pass a Pydantic model and the agent's FINAL RESULT will conform to it.

  This is different from UC06's Claude/OpenAI approach:
    Claude SDK:  Force a single API call to return JSON via tool_choice
    Agent SDK:   The ENTIRE agentic run (potentially multi-turn) produces
                 a final result that matches your schema

  Use case: "Run a multi-step research task, then give me a structured report"
  The agent might call 5 tools internally, then the FINAL OUTPUT is a Pydantic object.
  That's the Agent SDK's unique structured output value proposition.
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import BaseModel, Field
from typing import Optional
from shared.utils import load_env, header, require_key

load_env()
os.environ.setdefault("ANTHROPIC_API_KEY", require_key("ANTHROPIC_API_KEY"))

import claude_agent_sdk

ANTHROPIC_MODEL = "claude-sonnet-4-6"


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


async def extract_structured(text: str) -> StockAnalysis:
    """
    Use Agent SDK with output_schema for structured final result.
    The agent may use multiple turns internally but returns a validated object.
    """
    result_data = None

    async for event in claude_agent_sdk.query(
        prompt=f"Analyze this stock information and provide a structured analysis:\n\n{text}",
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=3,
            system_prompt=(
                "You are a stock analyst. Analyze the provided information and "
                "provide your analysis with: ticker, company, recommendation (BUY/HOLD/SELL), "
                "confidence (0.0-1.0), 3 key_reasons (list), target_price, risk_level (LOW/MEDIUM/HIGH). "
                "Return ONLY valid JSON matching this schema exactly."
            ),
            output_schema=StockAnalysis,    # ← Agent SDK structured output
        )
    ):
        if event.type == "result":
            # With output_schema, event.result is the structured object
            if hasattr(event, "result") and event.result:
                result_data = event.result
            elif hasattr(event, "output"):
                # Fallback: parse from output text
                import json
                try:
                    raw = event.output.strip()
                    if raw.startswith("```"):
                        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
                    result_data = StockAnalysis(**json.loads(raw))
                except Exception:
                    pass

    return result_data


async def simple_json_extract(text: str) -> dict:
    """Simpler approach: get JSON from assistant response text."""
    import json
    result_text = ""
    async for event in claude_agent_sdk.query(
        prompt=(
            f"Analyze this stock. Return ONLY a JSON object with keys: "
            f"ticker, company, recommendation, confidence, key_reasons, target_price, risk_level.\n\n{text}"
        ),
        options=claude_agent_sdk.ClaudeCodeOptions(
            model=ANTHROPIC_MODEL,
            max_turns=1,
            system_prompt="Return only valid JSON. No explanation."
        )
    ):
        if event.type == "assistant":
            for block in event.message.content:
                if hasattr(block, "text"):
                    result_text += block.text

    raw = result_text.strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
    return json.loads(raw.strip())


async def main():
    header("Claude Agent SDK", "06 — Structured Output", ANTHROPIC_MODEL)

    print("── Simple JSON extraction ──")
    result1 = await simple_json_extract(SAMPLE_TEXT)
    import json
    print(json.dumps(result1, indent=2))

    print("\n── Agent SDK output_schema (if supported) ──")
    result2 = await extract_structured(SAMPLE_TEXT)
    if result2:
        print(f"Ticker:         {result2.ticker}")
        print(f"Recommendation: {result2.recommendation}")
        print(f"Risk:           {result2.risk_level}")
    else:
        print("(output_schema not available in current version — use simple extraction)")

    print("\n── AGENT SDK STRUCTURED OUTPUT KEY POINT ──")
    print("output_schema = structured result from the ENTIRE agentic run")
    print("Use when: multi-step research that culminates in a structured report")
    print("Not for: single-call JSON extraction (use Claude SDK instead)")


if __name__ == "__main__":
    asyncio.run(main())
