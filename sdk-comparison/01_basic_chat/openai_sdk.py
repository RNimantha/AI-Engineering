"""
UC01 — Basic Chat | OpenAI Python SDK (openai)
═══════════════════════════════════════════════
KEY INSIGHT — OpenAI SDK:
  Very similar pattern to Claude SDK but with key structural differences:

  Claude SDK:  system= is a top-level parameter
  OpenAI SDK:  system message goes INSIDE the messages[] list as {"role": "system"}

  Claude SDK:  response.content[0].text
  OpenAI SDK:  response.choices[0].message.content

  Claude SDK:  response.usage.input_tokens / output_tokens
  OpenAI SDK:  response.usage.prompt_tokens / completion_tokens

  The OpenAI SDK is synchronous by default (like Claude SDK).
  You can use AsyncOpenAI for async.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"   # Fast + cheap for comparison demos


def basic_chat(user_message: str, system: str = "You are a helpful assistant.") -> str:
    """Single-turn using OpenAI SDK."""
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            # ⚠️ KEY DIFFERENCE: system goes INSIDE messages[] here
            {"role": "system",  "content": system},
            {"role": "user",    "content": user_message},
        ],
        max_tokens=1024,
    )
    # ⚠️ KEY DIFFERENCE: choices[0].message.content (not content[0].text)
    return response.choices[0].message.content


if __name__ == "__main__":
    header("OpenAI Python SDK (openai)", "01 — Basic Chat", OPENAI_MODEL)

    print("Q: What is the speed of light?")
    print("A:", basic_chat("What is the speed of light in km/s? One sentence only."))

    print("\nQ: Explain recursion (pirate persona)")
    pirate = basic_chat(
        user_message="Explain recursion in programming.",
        system="You are a pirate. Answer in pirate speak, max 2 sentences."
    )
    print("A:", pirate)

    print("\nQ: 3 laws of thermodynamics")
    print("A:", basic_chat(
        "List the 3 laws of thermodynamics. Format: numbered list, one line per law."
    ))

    # ── Side-by-side API diff ────────────────────────────────────────────────
    print("\n── API DIFF: Claude SDK vs OpenAI SDK ──")
    print("Claude: client.messages.create(system='...', messages=[user])")
    print("OpenAI: client.chat.completions.create(messages=[system, user])")
    print()
    print("Claude: response.content[0].text")
    print("OpenAI: response.choices[0].message.content")
    print()
    print("Claude: response.usage.input_tokens")
    print("OpenAI: response.usage.prompt_tokens")
