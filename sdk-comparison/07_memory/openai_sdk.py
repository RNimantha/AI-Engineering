"""
UC07 — Memory | OpenAI Python SDK
══════════════════════════════════
Same three memory strategies — identical concept, OpenAI syntax.
KEY DIFF: system message is inside messages[] list for OpenAI,
so memory management must account for the system message position.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from shared.utils import load_env, header, require_key

load_env()

OPENAI_MODEL = "gpt-4o-mini"


class ConversationMemory:
    def __init__(self, system: str = "You are a helpful assistant.", window: int = 10):
        self.client = OpenAI(api_key=require_key("OPENAI_API_KEY"))
        self.system = system
        self.window = window
        # ⚠️ OpenAI: system message INSIDE messages list
        self.messages = [{"role": "system", "content": system}]
        self.summary = ""

    def chat(self, user_message: str) -> str:
        """Full history — the base pattern."""
        self.messages.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=self.messages,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def chat_windowed(self, user_message: str) -> str:
        """Keep system + last N conversation turns."""
        self.messages.append({"role": "user", "content": user_message})
        # System is always first; keep last N pairs after it
        system_msg = self.messages[:1]
        conv_msgs = self.messages[1:]
        windowed = conv_msgs[-(self.window * 2):]
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=system_msg + windowed,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def chat_summarized(self, user_message: str, threshold: int = 8) -> str:
        self.messages.append({"role": "user", "content": user_message})
        conv_msgs = [m for m in self.messages if m["role"] != "system"]
        if len(conv_msgs) > threshold:
            old = conv_msgs[:-2]
            summary_text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
            sum_resp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system",  "content": "Summarize in 2-3 sentences."},
                    {"role": "user",    "content": summary_text},
                ]
            )
            self.summary = sum_resp.choices[0].message.content
            print(f"  [Compressed → {self.summary[:70]}...]")
            # Rebuild: system + summary + last exchange
            system_content = self.system
            if self.summary:
                system_content += f"\n\nConversation so far: {self.summary}"
            self.messages = [
                {"role": "system", "content": system_content}
            ] + conv_msgs[-2:]

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=self.messages,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        return reply


if __name__ == "__main__":
    header("OpenAI Python SDK", "07 — Memory / Multi-Turn", OPENAI_MODEL)

    mem = ConversationMemory()
    print("── Full history ──")
    print(f"T1: {mem.chat('My name is Rashmika and I love building AI agents.')}")
    print(f"T2: {mem.chat('What is my name?')}")
    print(f"T3: {mem.chat('What hobby did I mention?')}")
    print(f"T4: {mem.chat('Recommend 3 AI frameworks for me.')}")
    print(f"[Messages in memory: {len(mem.messages)}]")

    print("\n── Summarized memory ──")
    mem2 = ConversationMemory()
    mem2.chat_summarized("I own AAPL, NVDA, and MSFT.")
    mem2.chat_summarized("Bought AAPL at $150, NVDA at $400.")
    mem2.chat_summarized("Risk tolerance: medium.")
    mem2.chat_summarized("Want to retire in 10 years.")
    mem2.chat_summarized("What stocks do I own?")
    print(mem2.chat_summarized("Should I rebalance my portfolio?"))

    print("\n── KEY DIFF from Claude SDK ──")
    print("Claude: system= is a separate parameter, not in messages[]")
    print("OpenAI: system role is INSIDE messages[], must handle separately for windowing")
