"""
shared/utils.py
────────────────
Shared display helpers and env loader used across all examples.
"""
import os
import sys
from dotenv import load_dotenv

# Walk up until we find the .env file
def load_env():
    """Load .env from the project root (walks up from sdk-comparison/)."""
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        env_file = os.path.join(path, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
            return
        path = os.path.dirname(path)
    load_dotenv()  # fallback: look in cwd

def divider(title: str = ""):
    width = 60
    if title:
        pad = (width - len(title) - 2) // 2
        print(f"\n{'─' * pad} {title} {'─' * pad}")
    else:
        print("─" * width)

def header(sdk_name: str, use_case: str, model: str):
    print(f"\n{'═' * 60}")
    print(f"  SDK:       {sdk_name}")
    print(f"  Use Case:  {use_case}")
    print(f"  Model:     {model}")
    print(f"{'═' * 60}\n")

def require_key(key_name: str) -> str:
    val = os.environ.get(key_name)
    if not val:
        print(f"ERROR: {key_name} not set in .env")
        sys.exit(1)
    return val

def model_use(text):
    if text.startswith("claude"):
        return os.environ.get("CLAUDE_API_MODEL", "claude-haiku-4-5-20251001")
    elif text.startswith("gpt"):
        return os.environ.get("OPENAI_API_MODEL", "gpt-4.1-mini")
    return None

def total_usage(response):
    cost =(response.usage.input_tokens * (1/1000000) + response.usage.output_tokens * (5/1000000))
    return  cost