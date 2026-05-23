"""
UC02 — Streaming | LangGraph
══════════════════════════════
KEY INSIGHT — LangGraph streaming modes:
  LangGraph has THREE streaming modes, each answering a different question:

  1. stream_mode="values"   → full state snapshot after EACH node runs
                              "What is the entire state right now?"

  2. stream_mode="updates"  → only the CHANGES each node made to state
                              "What changed after this node ran?"

  3. stream_mode="messages" → token-by-token LLM output (like text streaming)
                              "What words is the LLM generating right now?"

  For a chat UI you use "messages". For observability/debugging you use
  "values" or "updates". You can combine modes: stream_mode=["values","messages"]

  This is LangGraph's biggest streaming advantage over plain SDKs:
  you can watch BOTH the LLM tokens AND the state machine transitions
  simultaneously.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


class ChatState(TypedDict):
    messages: Annotated[list, operator.add]
    system: str


def llm_node(state: ChatState) -> dict:
    llm = ChatOpenAI(model=OPENAI_MODEL, max_tokens=512, streaming=True)
    msgs = [SystemMessage(content=state["system"])] + state["messages"]
    response = llm.invoke(msgs)
    return {"messages": [response]}


def build_graph():
    g = StateGraph(ChatState)
    g.add_node("llm", llm_node)
    g.set_entry_point("llm")
    g.add_edge("llm", END)
    return g.compile()


def stream_values(prompt: str):
    """stream_mode='values' — get full state after each node."""
    app = build_graph()
    print("─── stream_mode='values' (full state per node) ───")
    for state_snapshot in app.stream(
        {"messages": [HumanMessage(content=prompt)], "system": "You are helpful."},
        stream_mode="values"
    ):
        # state_snapshot is the entire state dict after a node ran
        last_msg = state_snapshot["messages"][-1]
        if isinstance(last_msg, AIMessage):
            print(f"[After 'llm' node] Response: {last_msg.content}")


def stream_updates(prompt: str):
    """stream_mode='updates' — get only what changed per node."""
    app = build_graph()
    print("─── stream_mode='updates' (delta per node) ───")
    for node_name, updates in app.stream(
        {"messages": [HumanMessage(content=prompt)], "system": "You are helpful."},
        stream_mode="updates"
    ):
        print(f"[Node '{node_name}' produced update]")
        for key, val in updates.items():
            if key == "messages" and val:
                print(f"  messages[-1]: {val[-1].content[:80]}...")


def stream_tokens(prompt: str):
    """stream_mode='messages' — token-by-token output (best for chat UIs)."""
    app = build_graph()
    print("─── stream_mode='messages' (token-by-token) ───")
    print("Response: ", end="", flush=True)
    for chunk, metadata in app.stream(
        {"messages": [HumanMessage(content=prompt)], "system": "You are helpful."},
        stream_mode="messages"
    ):
        # chunk is a message fragment; metadata has {"langgraph_node": "llm", ...}
        if hasattr(chunk, "content") and chunk.content:
            print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    header("LangGraph", "02 — Streaming", OPENAI_MODEL)

    prompt = "Write a 3-sentence story about a robot learning to paint."

    stream_values(prompt)
    print()
    stream_tokens("What are 3 key principles of clean code? One line each.")

    print("\n── LANGGRAPH STREAMING ADVANTAGE ──")
    print("Other SDKs: stream LLM tokens OR observe state — not both")
    print("LangGraph:  stream_mode=['values', 'messages'] = tokens + state simultaneously")
    print("This is invaluable for debugging complex multi-agent workflows")
