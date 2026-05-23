"""
shared/tools.py
────────────────
Mock tools used consistently across ALL 10 use cases and ALL 4 SDKs.

Having one shared implementation means the comparison is pure:
the ONLY difference between the 4 files in each use case is how
each SDK defines, registers, and executes these exact same tools.

Tools available:
  calculate(expression)         → evaluates safe math expression
  get_weather(city)             → mock weather data
  search_web(query)             → mock web search results
  get_stock_price(ticker)       → mock stock prices
  send_email(to, subject, body) → mock email (logs only, never sends)
"""

from __future__ import annotations
import math
import re
from datetime import datetime


# ─────────────────────────────────────────────
# Tool Implementations (pure Python, no SDK)
# ─────────────────────────────────────────────

def calculate(expression: str) -> str:
    """
    Safely evaluate a math expression.
    Supports: +, -, *, /, **, sqrt, log, sin, cos, tan, pi, e
    """
    # Whitelist: only allow safe characters
    safe = re.match(r'^[\d\s\+\-\*\/\(\)\.\,\%\^sqrtlogsincoatpie]+$',
                    expression.lower().replace(" ", ""))
    if not safe:
        return f"ERROR: Unsafe expression '{expression}'"
    try:
        # Replace common math words with Python equivalents
        expr = expression.lower()
        expr = expr.replace("^", "**")
        expr = expr.replace("sqrt(", "math.sqrt(")
        expr = expr.replace("log(", "math.log(")
        expr = expr.replace("sin(", "math.sin(")
        expr = expr.replace("cos(", "math.cos(")
        expr = expr.replace("tan(", "math.tan(")
        expr = expr.replace("pi", str(math.pi))
        result = eval(expr, {"__builtins__": {}, "math": math})
        return f"{expression} = {round(float(result), 6)}"
    except Exception as e:
        return f"ERROR calculating '{expression}': {e}"


def get_weather(city: str) -> dict:
    """Mock weather API — returns fake but realistic data."""
    mock_data = {
        "london":    {"temp_c": 12, "condition": "Cloudy",  "humidity": 78, "wind_kmh": 20},
        "new york":  {"temp_c": 22, "condition": "Sunny",   "humidity": 55, "wind_kmh": 15},
        "tokyo":     {"temp_c": 28, "condition": "Humid",   "humidity": 85, "wind_kmh": 10},
        "sydney":    {"temp_c": 18, "condition": "Partly Cloudy", "humidity": 65, "wind_kmh": 25},
        "paris":     {"temp_c": 15, "condition": "Rainy",   "humidity": 82, "wind_kmh": 18},
        "dubai":     {"temp_c": 38, "condition": "Clear",   "humidity": 30, "wind_kmh": 12},
        "singapore": {"temp_c": 31, "condition": "Thunderstorm", "humidity": 90, "wind_kmh": 22},
    }
    city_lower = city.lower().strip()
    data = mock_data.get(city_lower, {
        "temp_c": 20, "condition": "Clear", "humidity": 60, "wind_kmh": 10
    })
    return {
        "city": city,
        "temperature_celsius": data["temp_c"],
        "temperature_fahrenheit": round(data["temp_c"] * 9/5 + 32, 1),
        "condition": data["condition"],
        "humidity_percent": data["humidity"],
        "wind_kmh": data["wind_kmh"],
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def search_web(query: str) -> list[dict]:
    """Mock web search — returns 3 fake results for any query."""
    return [
        {
            "title": f"Comprehensive guide to {query}",
            "url": f"https://example.com/guide/{query.replace(' ', '-').lower()}",
            "snippet": f"Everything you need to know about {query}. "
                       f"Updated {datetime.now().strftime('%B %Y')} with latest research.",
        },
        {
            "title": f"{query} — Wikipedia",
            "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
            "snippet": f"{query} is a topic with extensive documentation. "
                       f"Key aspects include definitions, history, and current developments.",
        },
        {
            "title": f"Latest news on {query}",
            "url": f"https://news.example.com/{query.replace(' ', '-').lower()}",
            "snippet": f"Recent developments in {query} show significant progress. "
                       f"Experts weigh in on implications for 2025 and beyond.",
        },
    ]


def get_stock_price(ticker: str) -> dict:
    """Mock stock price lookup."""
    mock_prices = {
        "AAPL":  {"price": 189.50, "change": +1.2,  "company": "Apple Inc."},
        "GOOGL": {"price": 175.30, "change": -0.8,  "company": "Alphabet Inc."},
        "MSFT":  {"price": 415.20, "change": +2.1,  "company": "Microsoft Corp."},
        "TSLA":  {"price": 248.10, "change": -3.5,  "company": "Tesla Inc."},
        "NVDA":  {"price": 875.60, "change": +12.4, "company": "NVIDIA Corp."},
        "AMZN":  {"price": 192.40, "change": +0.9,  "company": "Amazon.com Inc."},
        "META":  {"price": 512.70, "change": +4.3,  "company": "Meta Platforms"},
    }
    ticker_upper = ticker.upper().strip()
    data = mock_prices.get(ticker_upper, {
        "price": 100.00, "change": 0.0, "company": f"Unknown ({ticker_upper})"
    })
    return {
        "ticker": ticker_upper,
        "company": data["company"],
        "price_usd": data["price"],
        "change_percent": data["change"],
        "market": "NASDAQ",
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def send_email(to: str, subject: str, body: str) -> dict:
    """Mock email sender — logs the action, never actually sends."""
    print(f"\n📧 [MOCK EMAIL SENT]\n   To: {to}\n   Subject: {subject}\n   Body: {body[:80]}...")
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "message_id": f"mock-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


# ─────────────────────────────────────────────
# Tool registry — maps name → function
# Used by the manual agentic loops (Claude SDK, OpenAI SDK)
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "calculate":      calculate,
    "get_weather":    get_weather,
    "search_web":     search_web,
    "get_stock_price": get_stock_price,
    "send_email":     send_email,
}

def execute_tool(name: str, args: dict) -> str:
    """Dispatch a tool call by name and return a string result."""
    import json
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"ERROR: Unknown tool '{name}'"
    result = fn(**args)
    return json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)


# ─────────────────────────────────────────────
# Schema definitions per SDK format
# ─────────────────────────────────────────────

# ── Anthropic format (Claude SDK + Agent SDK) ──
ANTHROPIC_TOOLS = [
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports +,-,*,/,**,sqrt,log,sin,cos,tan,pi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "The math expression to evaluate, e.g. '2 ** 10' or 'sqrt(144)'"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_weather",
        "description": "Get current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'London', 'Tokyo'"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "search_web",
        "description": "Search the web and return top 3 results for a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_stock_price",
        "description": "Get the current stock price for a ticker symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol, e.g. 'AAPL', 'NVDA'"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email. Use only when explicitly asked to send/email something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to":      {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body":    {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"]
        }
    },
]

# ── OpenAI format ──
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Supports +,-,*,/,**,sqrt,log,sin,cos,tan,pi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The math expression to evaluate"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get current stock price for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to":      {"type": "string"},
                    "subject": {"type": "string"},
                    "body":    {"type": "string"},
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
]
