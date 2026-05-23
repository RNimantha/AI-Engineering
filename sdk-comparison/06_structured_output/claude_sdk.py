"""
UC06 — Structured Output | Claude SDK (anthropic)
══════════════════════════════════════════════════
KEY INSIGHT — Getting structured JSON from Claude:
  Real-world agents need to EXTRACT structured data from LLM responses.
  "Give me a JSON object with these fields" is core agentic infrastructure —
  you need it to pass data between agents, store to databases, validate.

  THREE approaches, from simplest to most robust:

  Approach 1: Prompt engineering
    Ask Claude to return JSON, parse with json.loads()
    Risk: Claude might add explanation text, breaking json.loads()

  Approach 2: JSON mode via tool use (RECOMMENDED for Claude)
    Define a "extract_data" tool with your exact schema
    Force Claude to call it: tool_choice={"type":"tool","name":"extract_data"}
    Claude MUST return your exact JSON — no text wrapping possible
    This is the most reliable way on Claude SDK

  Approach 3: Pydantic + tool schema (production grade)
    Auto-generate the tool schema from a Pydantic model
    Validate the output with Pydantic — type safety guaranteed
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from pydantic import BaseModel, Field
from typing import Optional
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"


# ── Data model ────────────────────────────────────────────────────────────────

class StockAnalysis(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    company: str = Field(description="Full company name")
    recommendation: str = Field(description="BUY, HOLD, or SELL")
    confidence: float = Field(description="Confidence score 0.0 to 1.0")
    key_reasons: list[str] = Field(description="List of 3 reasons for recommendation")
    target_price: Optional[float] = Field(None, description="12-month price target in USD")
    risk_level: str = Field(description="LOW, MEDIUM, or HIGH")


# ── Approach 1: Simple JSON prompting ────────────────────────────────────────

def extract_json_prompt(text: str) -> dict:
    """Ask Claude to return JSON. Works but brittle."""
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system="You are a data extractor. Always respond with valid JSON only. No explanation.",
        messages=[{"role": "user", "content": f"Extract stock info as JSON:\n{text}"}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
    return json.loads(raw.strip())


# ── Approach 2: Tool use as JSON schema enforcer (RECOMMENDED) ───────────────

def extract_structured(text: str) -> StockAnalysis:
    """
    RECOMMENDED: Use a tool definition to enforce exact JSON schema.
    tool_choice forces Claude to call the tool — no free text possible.
    """
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))

    # Build tool schema from Pydantic model
    schema = StockAnalysis.model_json_schema()

    extraction_tool = {
        "name": "record_analysis",
        "description": "Record a structured stock analysis",
        "input_schema": schema,
    }

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        tools=[extraction_tool],
        tool_choice={"type": "tool", "name": "record_analysis"},  # FORCE the tool call
        messages=[{
            "role": "user",
            "content": f"Analyze this stock information and record your analysis:\n\n{text}"
        }],
    )

    # Find the tool_use block and extract its input
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_analysis":
            return StockAnalysis(**block.input)   # Pydantic validates!

    raise ValueError("No tool call in response")


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "06 — Structured Output", ANTHROPIC_MODEL)

    sample_text = """
    NVIDIA (NVDA) has been dominating the AI chip market.
    Trading at $875.60 today (+12.4%).
    Strong buy momentum driven by data center demand.
    Some risk from China export restrictions.
    Analysts consensus is bullish with targets of $950-1000.
    """

    print("── Approach 1: JSON prompting ──")
    result1 = extract_json_prompt(sample_text)
    print(json.dumps(result1, indent=2))

    print("\n── Approach 2: Tool-enforced schema (RECOMMENDED) ──")
    result2 = extract_structured(sample_text)
    print(f"Ticker:         {result2.ticker}")
    print(f"Recommendation: {result2.recommendation}")
    print(f"Confidence:     {result2.confidence:.0%}")
    print(f"Risk Level:     {result2.risk_level}")
    print(f"Key Reasons:")
    for r in result2.key_reasons:
        print(f"  • {r}")
    print(f"Target Price:   ${result2.target_price}")

    print("\n── WHY TOOL-FORCED IS BETTER ──")
    print("Prompt approach: Claude might say 'Here is the JSON: {...}' → breaks json.loads()")
    print("Tool approach:   Claude MUST return valid JSON matching your schema → always works")
    print("Pydantic:        Type validation, default values, field descriptions auto-documented")
