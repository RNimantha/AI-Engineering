"""
UC01 — Basic Chat | LangGraph
══════════════════════════════
KEY INSIGHT — LangGraph:
  LangGraph is a STATE MACHINE framework, NOT a chat client.
  For basic chat, it's the most verbose of all 4 SDKs — 3x more code
  for the same result. That's intentional: LangGraph earns its complexity
  in UC08+ (supervisor, human-in-the-loop, conditional routing).

  Core LangGraph concepts introduced here:
    StateGraph  → a directed graph where nodes process state
    State       → a TypedDict that flows through nodes (shared memory)
    Node        → a Python function that takes state, returns state update
    add_edge    → wires nodes together (A → B)
    compile()   → freezes the graph into an executable app
    invoke()    → runs the graph with an initial state

  For basic chat, the "graph" has just ONE node: the LLM call.
  You'll see why this becomes powerful in UC09 (Supervisor pattern).
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


# ── Step 1: Define State ─────────────────────────────────────────────────────
# State is a TypedDict that every node reads from and writes to.
# Annotated[list, operator.add] means new messages get APPENDED, not overwritten.
# This is LangGraph's "reducer" pattern for message history.

class ChatState(TypedDict):
    messages: Annotated[list, operator.add]   # message history
    system:   str                              # system prompt


# ── Step 2: Define Nodes ─────────────────────────────────────────────────────
# Each node is a function: (state) → dict of state updates

def llm_node(state: ChatState) -> dict:
    """The one node in our graph — calls the LLM."""
    llm = ChatOpenAI(model=OPENAI_MODEL, max_tokens=1024)

    # Build the full message list including system prompt
    messages = [SystemMessage(content=state["system"])] + state["messages"]
    response = llm.invoke(messages)

    # Return a state update — messages gets APPENDED (reducer)
    return {"messages": [response]}


# ── Step 3: Build the Graph ──────────────────────────────────────────────────

def build_graph() -> object:
    graph = StateGraph(ChatState)
    graph.add_node("llm", llm_node)       # add the node
    graph.set_entry_point("llm")          # start here
    graph.add_edge("llm", END)            # after llm, we're done
    return graph.compile()


def basic_chat(user_message: str, system: str = "You are a helpful assistant.") -> str:
    app = build_graph()

    # invoke() runs the full graph synchronously
    result = app.invoke({
        "messages": [HumanMessage(content=user_message)],
        "system": system,
    })

    # The last message in state is the AI response
    return result["messages"][-1].content


if __name__ == "__main__":
    header("LangGraph (langchain-openai)", "01 — Basic Chat", OPENAI_MODEL)

    print("Q: What is the speed of light?")
    print("A:", basic_chat("What is the speed of light in km/s? One sentence only."))

    print("\nQ: Explain recursion (pirate persona)")
    print("A:", basic_chat(
        "Explain recursion in programming.",
        system="You are a pirate. Answer in pirate speak, max 2 sentences."
    ))

    # ── What you learn here ──────────────────────────────────────────────────
    print("\n── WHY LANGGRAPH FOR BASIC CHAT? ──")
    print("✗ More code than Claude/OpenAI SDK for same result")
    print("✓ But NOW you have a graph you can extend:")
    print("  → Add a 'memory' node before llm_node")
    print("  → Add a 'router' node that picks specialist LLMs")
    print("  → Add a 'human_review' node that pauses for approval")
    print("  → Add cycles for retry logic")
    print("  → Add checkpointing for session persistence")
    print()
    print("The graph declaration is the investment —")
    print("it pays dividends in UC08, UC09, UC10.")
