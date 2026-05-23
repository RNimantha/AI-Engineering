"""
UC07 — Memory | LangGraph
══════════════════════════
KEY INSIGHT — LangGraph checkpointing:
  LangGraph's memory superpower: PERSISTENT CHECKPOINTS.
  Every state transition is saved to a store (SQLite, PostgreSQL, Redis).
  You can resume a conversation from ANY previous state, even after restart.

  thread_id = conversation identifier (like session_id in Agent SDK)
  config = {"configurable": {"thread_id": "my-chat-1"}}

  This solves three problems simultaneously:
    1. Multi-turn memory  → state accumulates messages across calls
    2. Crash recovery     → resume from last checkpoint after crash
    3. Time travel        → replay from any historical state for debugging

  Also shown: MemorySaver (in-memory, dev/test) vs SqliteSaver (persistent)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver    # in-memory (dev)
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import operator

from shared.utils import load_env, header, require_key

load_env()
os.environ["OPENAI_API_KEY"] = require_key("OPENAI_API_KEY")

OPENAI_MODEL = "gpt-4o-mini"


class ChatState(TypedDict):
    messages: Annotated[list, operator.add]


def llm_node(state: ChatState) -> dict:
    llm = ChatOpenAI(model=OPENAI_MODEL, max_tokens=512)
    msgs = [SystemMessage(content="You are a helpful assistant.")] + state["messages"]
    return {"messages": [llm.invoke(msgs)]}


def build_graph_with_memory():
    """Add checkpointer to compile() — that's all it takes for persistence."""
    g = StateGraph(ChatState)
    g.add_node("llm", llm_node)
    g.set_entry_point("llm")
    g.add_edge("llm", END)

    checkpointer = MemorySaver()    # For production: SqliteSaver.from_conn_string("chat.db")
    return g.compile(checkpointer=checkpointer)


def multi_turn_chat():
    app = build_graph_with_memory()

    # thread_id identifies the conversation — like a session ID
    config = {"configurable": {"thread_id": "rashmika-chat-001"}}

    def chat(user_msg: str) -> str:
        result = app.invoke(
            {"messages": [HumanMessage(content=user_msg)]},
            config=config    # ← same config = same thread = memory persists
        )
        return result["messages"][-1].content

    return chat


def demo_time_travel(app, config):
    """
    LangGraph's unique feature: replay from any historical checkpoint.
    This is invaluable for debugging multi-agent systems.
    """
    print("\n── Time travel: all checkpoints ──")
    for state, metadata in app.get_state_history(config):
        msg_count = len(state.values.get("messages", []))
        step = metadata.get("step", "?")
        ts = metadata.get("created_at", "?")
        print(f"  Step {step}: {msg_count} messages in state (ts: {ts})")


if __name__ == "__main__":
    header("LangGraph", "07 — Memory / Multi-Turn", OPENAI_MODEL)

    app = build_graph_with_memory()
    config = {"configurable": {"thread_id": "rashmika-chat-001"}}

    def chat(msg):
        result = app.invoke({"messages": [HumanMessage(content=msg)]}, config=config)
        return result["messages"][-1].content

    print("── Multi-turn with checkpointing ──")
    print(f"T1: {chat('My name is Rashmika and I love building AI agents.')}")
    print(f"T2: {chat('What is my name?')}")
    print(f"T3: {chat('What hobby did I mention?')}")
    print(f"T4: {chat('Recommend 3 AI frameworks for me to learn.')}")

    demo_time_travel(app, config)

    print("\n── LANGGRAPH MEMORY UNIQUE FEATURES ──")
    print("1. Checkpointing: state saved automatically after every node")
    print("2. thread_id: resumable conversations with zero extra code")
    print("3. Time travel: replay from any historical state")
    print("4. Branching: fork a conversation from a past checkpoint")
    print()
    print("SqliteSaver example (persistent across restarts):")
    print("  from langgraph.checkpoint.sqlite import SqliteSaver")
    print("  checkpointer = SqliteSaver.from_conn_string('conversations.db')")
    print("  app = graph.compile(checkpointer=checkpointer)")
    print("  → conversations survive Python process restarts!")
