"""
UC02 — Streaming | OpenAI Python SDK
══════════════════════════════════════
KEY INSIGHT — OpenAI streaming:
  Very similar to Claude SDK but the stream object is a different type.

  Claude SDK: client.messages.stream() context manager → .text_stream
  OpenAI SDK: client.chat.completions.create(stream=True) → iterate chunks

  OpenAI gives you ChatCompletionChunk objects.
  Each chunk has: choices[0].delta.content (the text fragment)
  The stream ends when choices[0].finish_reason is not None.

  Newer OpenAI SDK also supports a streaming context manager pattern
  (similar to Claude's) via client.beta.chat.completions.stream()
  which gives you nicer access to the final accumulated message.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"


def stream_response(prompt: str, system: str = "You are a helpful assistant."):
    """Stream tokens to stdout — basic approach."""
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))

    print("Response: ", end="", flush=True)

    # stream=True returns an iterator of ChatCompletionChunk
    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=512,
        stream=True,           # ← This is the key difference vs UC01
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
    )

    full_text = ""
    for chunk in stream:
        # Each chunk: choices[0].delta.content is the text fragment (can be None)
        text_fragment = chunk.choices[0].delta.content
        if text_fragment is not None:
            print(text_fragment, end="", flush=True)
            full_text += text_fragment

        # chunk.choices[0].finish_reason is set on the last chunk
        # Values: "stop", "length", "tool_calls", "content_filter", None

    print()  # newline after stream
    return full_text


def stream_with_context_manager(prompt: str):
    """
    Cleaner approach using OpenAI's streaming context manager (SDK >= 1.7).
    Similar to Claude SDK's stream pattern.
    """
    client = OpenAI(api_key=require_key("OPENAI_API_KEY"))

    print("Response: ", end="", flush=True)

    # client.beta.chat.completions.stream() gives you:
    # - stream.text_stream  (like Claude SDK!)
    # - stream.get_final_completion() for the full message after
    with client.beta.chat.completions.stream(
        model=OPENAI_MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": prompt},
        ]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)

    print()
    final = stream.get_final_completion()
    return final


if __name__ == "__main__":
    header("OpenAI Python SDK", "02 — Streaming", OPENAI_MODEL)

    print("Prompt: Write a 3-sentence story about a robot learning to paint.\n")
    stream_response(
        "Write a 3-sentence story about a robot learning to paint.",
        system="You are a creative writing assistant."
    )

    print("\n── Context manager approach (cleaner) ──")
    print("Prompt: What are 5 key principles of clean code?\n")
    final = stream_with_context_manager("List 5 key principles of clean code. Be concise.")
    print(f"\n[Finish reason: {final.choices[0].finish_reason}]")

    print("\n── STREAMING DIFF ──")
    print("Claude SDK: with client.messages.stream() as s: for t in s.text_stream")
    print("OpenAI SDK: stream=True, for chunk in stream: chunk.choices[0].delta.content")
    print("OpenAI new: with client.beta.chat.completions.stream() as s: s.text_stream")
