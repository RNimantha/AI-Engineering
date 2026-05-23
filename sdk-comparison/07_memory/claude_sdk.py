"""
UC07 — Memory / Multi-Turn Conversation | Claude SDK
═════════════════════════════════════════════════════
KEY INSIGHT — Memory in LLMs:
  LLMs are stateless. Each API call has no memory of previous calls.
  "Memory" = manually maintaining the messages[] list between turns.

  Three memory patterns:

  1. Full history (in-context memory):
     Keep ALL messages. Simple. Works perfectly for short conversations.
     Limitation: hits context window limit for long chats (~200K tokens for Claude).

  2. Windowed memory:
     Keep only the last N turns. Oldest messages are dropped.
     Tradeoff: agent forgets old info but stays within context limit.

  3. Summarized memory:
     Periodically ask the LLM to summarize old messages.
     Store the summary, drop old messages. Best for long-running agents.

  The messages[] list IS the memory. There's no hidden magic.
  This is why multi-agent pipelines are careful about what they carry forward.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from shared.utils import load_env, header, require_key

load_env()

ANTHROPIC_MODEL = "claude-sonnet-4-6"


class ConversationMemory:
    """A simple conversation manager with three memory strategies."""

    def __init__(self, window_size: int = 10):
        self.client = anthropic.Anthropic(api_key=require_key("ANTHROPIC_API_KEY"))
        self.messages = []
        self.window_size = window_size  # for windowed strategy
        self.summary = ""               # for summarized strategy

    # ── Strategy 1: Full history ─────────────────────────────────────────────

    def chat_full(self, user_message: str, system: str = "You are a helpful assistant.") -> str:
        """Keep all messages — simple and complete."""
        self.messages.append({"role": "user", "content": user_message})
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            messages=self.messages,
        )
        reply = response.content[0].text
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    # ── Strategy 2: Windowed history ─────────────────────────────────────────

    def chat_windowed(self, user_message: str, system: str = "You are a helpful assistant.") -> str:
        """Keep only last N turns to control context size."""
        self.messages.append({"role": "user", "content": user_message})
        # Keep only last window_size messages (pairs of user+assistant)
        windowed = self.messages[-(self.window_size * 2):]
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            messages=windowed,
        )
        reply = response.content[0].text
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    # ── Strategy 3: Summarised memory ────────────────────────────────────────

    def chat_summarized(self, user_message: str, threshold: int = 6) -> str:
        """Compress old messages into a summary when history gets long."""
        self.messages.append({"role": "user", "content": user_message})

        # Summarize when we accumulate threshold messages
        if len(self.messages) > threshold:
            old_messages = self.messages[:-2]  # everything except last exchange
            self.summary = self._summarize(old_messages)
            self.messages = self.messages[-2:]  # keep only last exchange
            print(f"  [Memory compressed — summary: {self.summary[:80]}...]")

        # Include summary as system context
        system = "You are a helpful assistant."
        if self.summary:
            system += f"\n\nConversation summary so far:\n{self.summary}"

        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            messages=self.messages,
        )
        reply = response.content[0].text
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def _summarize(self, messages: list) -> str:
        """Ask Claude to summarize a list of messages."""
        msg_text = "\n".join([
            f"{m['role'].upper()}: {m['content']}" for m in messages
        ])
        response = self.client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": f"Summarize this conversation in 2-3 sentences:\n{msg_text}"
            }]
        )
        return response.content[0].text

    def clear(self):
        self.messages = []
        self.summary = ""
        return self


if __name__ == "__main__":
    header("Claude SDK (anthropic)", "07 — Memory / Multi-Turn", ANTHROPIC_MODEL)

    # ── Demo: Agent remembers facts across turns ──
    mem = ConversationMemory()

    print("── Full history memory demo ──")
    print(f"Turn 1: {mem.chat_full('My name is Rashmika and I love building AI agents.')}")
    print(f"Turn 2: {mem.chat_full('What is my name?')}")
    print(f"Turn 3: {mem.chat_full('What hobby did I mention?')}")
    print(f"Turn 4: {mem.chat_full('Recommend 3 AI frameworks I should learn.')}")
    print(f"\n[Messages in memory: {len(mem.messages)}]")

    print("\n── Summarized memory (compresses after 6 messages) ──")
    mem2 = ConversationMemory()
    mem2.chat_summarized("My portfolio has AAPL, NVDA, and MSFT.")
    mem2.chat_summarized("I bought AAPL at $150 and NVDA at $400.")
    mem2.chat_summarized("My risk tolerance is medium.")
    mem2.chat_summarized("I want to retire in 10 years.")
    mem2.chat_summarized("What stocks do I own?")  # triggers compression
    print(mem2.chat_summarized("Given my goals, should I rebalance?"))

    print("\n── MEMORY INSIGHT ──")
    print("Full history:  simple, perfect recall, context limit risk")
    print("Windowed:      constant memory size, loses old info")
    print("Summarized:    best balance, requires extra LLM call to compress")
    print()
    print("For production agents: use a vector DB for long-term memory (UC beyond 10)")
