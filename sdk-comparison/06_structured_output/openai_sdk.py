"""
UC06 — Structured Output | OpenAI Python SDK
══════════════════════════════════════════════
KEY INSIGHT — OpenAI has TWO structured output mechanisms:

  1. response_format={"type":"json_object"}  (older, JSON mode)
     → Guarantees valid JSON but NOT schema adherence
     → You define the schema only via the system prompt (unverified)
     → Can still return wrong fields

  2. response_format=StockAnalysis (Structured Outputs, newer)
     → Guarantees SCHEMA adherence using your Pydantic model
     → Uses client.beta.chat.completions.parse()
     → response.choices[0].message.parsed is already your Pydantic object!
     → This is the cleanest structured output of all 4 SDKs

  3. tool_choice="required" + function definition (like Claude SDK approach)
     → Also guarantees schema, but more verbose than beta.parse()

  RECOMMENDATION: Use beta.parse() — it's the most elegant.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"


class StockAnalysis(BaseModel):
    ticker: str
    company: str
    recommendation: str          # BUY, HOLD, or SELL
    confidence: float            # 0.0 to 1.0
    key_reasons: list[str]       # 3 reasons
    target_price: Optional[float] = None
    risk_level: str              # LOW, MEDIUM, HIGH


SAMPLE_TEXT = """
NVIDIA (NVDA) has been dominating the AI chip market.
Trading at $875.60 today (+12.4%).
Strong buy momentum driven by data center demand.
Some risk from China export restrictions.
Analysts consensus is bullish with targets of $950-1000.
"""


# ── Approach 1: JSON mode (old way) ──────────────────────────────────────────

def json_mode(text: str) -> dict:
    """JSON mode guarantees valid JSON but NOT correct fields."""
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},   # guarantees valid JSON
        messages=[
            {"role": "system", "content":
             "Return a JSON with: ticker, company, recommendation (BUY/HOLD/SELL), "
             "confidence (0-1), key_reasons (list), target_price, risk_level."},
            {"role": "user", "content": f"Analyze:\n{text}"},
        ]
    )
    return json.loads(response.choices[0].message.content)


# ── Approach 2: beta.parse() — RECOMMENDED ───────────────────────────────────

def structured_parse(text: str) -> StockAnalysis:
    """
    BEST APPROACH: Pydantic model directly in response_format.
    The SDK handles schema generation + parsing automatically.
    """
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
    response = client.beta.chat.completions.parse(
        model=OPENAI_MODEL,
        response_format=StockAnalysis,             # ← your Pydantic model!
        messages=[
            {"role": "system", "content": "You are a stock analyst. Be precise."},
            {"role": "user",   "content": f"Analyze this stock:\n{text}"},
        ]
    )
    # .parsed is already a StockAnalysis instance — no json.loads needed!
    return response.choices[0].message.parsed


if __name__ == "__main__":
    header("OpenAI Python SDK", "06 — Structured Output", OPENAI_MODEL)

    print("── Approach 1: JSON mode ──")
    result1 = json_mode(SAMPLE_TEXT)
    print(json.dumps(result1, indent=2))

    print("\n── Approach 2: beta.parse() (RECOMMENDED) ──")
    result2 = structured_parse(SAMPLE_TEXT)
    print(f"Ticker:         {result2.ticker}")
    print(f"Recommendation: {result2.recommendation}")
    print(f"Confidence:     {result2.confidence:.0%}")
    print(f"Risk:           {result2.risk_level}")
    for r in result2.key_reasons:
        print(f"  • {r}")
    print(f"Target:         ${result2.target_price}")

    print("\n── OPENAI vs CLAUDE STRUCTURED OUTPUT ──")
    print("OpenAI beta.parse():   response.choices[0].message.parsed → Pydantic object")
    print("Claude tool-forced:    block.input → dict → StockAnalysis(**block.input)")
    print()
    print("OpenAI is slightly cleaner for structured output.")
    print("Claude's tool approach is equally reliable but one extra step.")
