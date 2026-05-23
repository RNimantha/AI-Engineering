"""
UC02 — Streaming | Claude SDK (anthropic)
═══════════════════════════════════════════
KEY INSIGHT — Streaming with Claude SDK:
  Instead of waiting for the full response, you get tokens as they're generated.
  Use client.messages.stream() as a context manager.

  Two streaming approaches:
    1. .text_stream  → yields raw text strings (simple)
    2. .stream()     → yields typed events (InputJsonDelta, TextDelta, etc.)
       gives you granular control: detect when tool calls start, track usage

  Why streaming matters:
    - Perceived latency drops dramatically (user sees words appearing)
    - For long responses (reports, essays) you don't wait 30s for anything
    - Essential for chat UIs, voice systems, real-time dashboards
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"


def stream_response(prompt: str, system: str = "You are a helpful assistant."):
    """Stream tokens to stdout as they arrive."""
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))

    print("Response: ", end="", flush=True)

    # context manager approach — handles connection lifecycle automatically
    with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        # .text_stream yields str chunks as they arrive
        for text_chunk in stream.text_stream:
            print(text_chunk, end="", flush=True)   # print WITHOUT newline

    print()  # newline after stream ends

    # After the context manager exits, you can access the final message
    # stream.get_final_message() returns the complete Message object
    final = stream.get_final_message()
    return final


def stream_with_events(prompt: str):
    """
    Advanced: stream typed events to track tool use, usage, etc.
    Useful when you want to detect WHEN Claude starts calling a tool mid-stream.
    """
    client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))

    with client.messages.stream(
        model=ANTHROPIC_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for event in stream:
            # Event types: RawMessageStartEvent, RawContentBlockStartEvent,
            #              RawContentBlockDeltaEvent, RawContentBlockStopEvent,
            #              RawMessageDeltaEvent, RawMessageStopEvent
            if hasattr(event, 'type'):
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        print(event.delta.text, end="", flush=True)
                elif event.type == "message_delta":
                    # Contains stop_reason and usage delta
                    pass
    print()


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "02 — Streaming", ANTHROPIC_MODEL)

    print("Prompt: Write a 3-sentence story about a robot learning to paint.\n")
    final_msg = stream_response(
        "Write a 3-sentence story about a robot learning to paint.",
        system="You are a creative writing assistant."
    )
    print(f"\n[Total tokens: {final_msg.usage.input_tokens} in / {final_msg.usage.output_tokens} out]")

    print("\n── Advanced event streaming ──")
    print("Prompt: What are 5 key principles of clean code?\n")
    print("Response: ", end="")
    stream_with_events("List 5 key principles of clean code. Be concise.")
