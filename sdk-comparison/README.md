# SDK Comparison — Agentic Systems: Claude SDK vs Claude Agent SDK vs OpenAI SDK vs LangGraph

A complete, side-by-side comparison of all four SDKs across 10 use cases — from basic chat to production-grade multi-agent systems with human-in-the-loop workflows.

---

## Setup

```bash
cd sdk-comparison
pip install anthropic openai langchain-openai langgraph python-dotenv httpx
```

Create a `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

---

## SDK Quick Reference

| | Claude SDK | Claude Agent SDK | OpenAI SDK | LangGraph |
|---|---|---|---|---|
| **Package** | `anthropic` | `claude-agent-sdk` | `openai` | `langgraph` |
| **Model** | claude-sonnet-4-6 | claude-sonnet-4-6 | gpt-4o-mini | gpt-4o-mini |
| **Style** | Synchronous | Async generator | Synchronous | Graph / nodes |
| **Tool args** | Python dict | Built-in tools | JSON string | Auto-dispatched |
| **System prompt** | Top-level param | `system_prompt=` option | Inside `messages[]` | `SystemMessage` node |
| **Response** | `response.content[0].text` | Event stream | `choices[0].message.content` | State dict |
| **Memory** | Manual `messages[]` | `session_id` + `resume=` | Manual `messages[]` | Checkpointer + `thread_id` |
| **Loop control** | Manual `while True` | `max_turns=` | Manual `while True` | Graph edges |
| **HITL** | Manual gate in loop | `max_turns=1` + resume | Manual gate in loop | `interrupt_before=` |

---

## Use Case Progression

### UC01 — Basic Chat
**Concept:** Single-turn LLM call. The foundation of everything.

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | `client.messages.create(system=..., messages=[...])` |
| Agent SDK | `async for event in claude_agent_sdk.query(prompt=...)` |
| OpenAI SDK | System prompt goes **inside** `messages[]` as `{"role":"system"}` |
| LangGraph | `StateGraph` + single node + `llm.invoke()` |

```bash
python 01_basic_chat/claude_sdk.py
python 01_basic_chat/agent_sdk.py
python 01_basic_chat/openai_sdk.py
python 01_basic_chat/langgraph.py
```

---

### UC02 — Streaming
**Concept:** Receive tokens as they are generated instead of waiting for the full response.

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | `with client.messages.stream() as s: for text in s.text_stream` |
| Agent SDK | Events arrive naturally — assistant events stream per turn |
| OpenAI SDK | `stream=True` or `client.beta.chat.completions.stream()` |
| LangGraph | `app.stream(..., stream_mode="messages")` for token-level |

```bash
python 02_streaming/claude_sdk.py
python 02_streaming/agent_sdk.py
python 02_streaming/openai_sdk.py
python 02_streaming/langgraph.py
```

---

### UC03 — Single Tool Use
**Concept:** Give the LLM one tool. Build the full Reason → Act → Observe loop.

**This is the most important use case** — everything more complex is built on this loop.

| SDK | Loop trigger | Tool args | Tool result format |
|-----|-------------|-----------|-------------------|
| Claude SDK | `stop_reason == "tool_use"` | `block.input` (dict) | `{"type":"tool_result", "tool_use_id":...}` |
| Agent SDK | Built-in — `allowed_tools=["Bash"]` | Handled internally | Handled internally |
| OpenAI SDK | `finish_reason == "tool_calls"` | `json.loads(arguments)` | `{"role":"tool", "tool_call_id":...}` |
| LangGraph | `ToolNode` + conditional edge + cycle | Auto-dispatched | Auto-appended to state |

```bash
python 03_single_tool/claude_sdk.py
python 03_single_tool/agent_sdk.py
python 03_single_tool/openai_sdk.py
python 03_single_tool/langgraph.py
```

---

### UC04 — Multi-Tool Use
**Concept:** Multiple tools available. Agent picks the right one(s) for each step.

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | Pass `tools=[tool1, tool2, ...]`, same loop |
| Agent SDK | `allowed_tools=["Bash", "WebSearch"]` — built-in tools only |
| OpenAI SDK | `parallel_tool_calls=True` — can call multiple tools in one turn |
| LangGraph | `create_react_agent(llm, tools=[...])` — one-liner full ReAct agent |

```bash
python 04_multi_tool/claude_sdk.py
python 04_multi_tool/agent_sdk.py
python 04_multi_tool/openai_sdk.py
python 04_multi_tool/langgraph.py
```

---

### UC05 — ReAct Loop (Multi-step Reasoning)
**Concept:** Agent reasons across multiple steps, using tools repeatedly to build toward an answer.

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | Same `while True` loop — just runs more iterations |
| Agent SDK | `max_turns=10` — let the agent reason for up to N turns |
| OpenAI SDK | Same `while True` loop with `max_tokens` budget |
| LangGraph | Custom `tool_tracker_node` between agent ↔ tools; extended state with `reasoning_log` |

```bash
python 05_react_loop/claude_sdk.py
python 05_react_loop/agent_sdk.py
python 05_react_loop/openai_sdk.py
python 05_react_loop/langgraph.py
```

---

### UC06 — Structured Output
**Concept:** Force the LLM to return a specific JSON schema — validated as a Pydantic model.

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | `tool_choice={"type":"tool","name":"extract_data"}` — forces a single tool call as JSON schema |
| Agent SDK | Prompt engineering + JSON parsing — no native structured output |
| OpenAI SDK | `client.beta.chat.completions.parse(response_format=PydanticModel)` → `.parsed` is already typed |
| LangGraph | `llm.with_structured_output(Model)` + retry node on parse failure |

**Winner for structured output: OpenAI** — `.parsed` is the cleanest API.

```bash
python 06_structured_output/claude_sdk.py
python 06_structured_output/agent_sdk.py
python 06_structured_output/openai_sdk.py
python 06_structured_output/langgraph.py
```

---

### UC07 — Memory & Conversation History
**Concept:** Maintain context across multiple turns or sessions.

| SDK | Strategy | Persistence |
|-----|----------|-------------|
| Claude SDK | Append to `messages[]` — full history, windowed, or summarized | ❌ In-memory only |
| Agent SDK | `session_id` + `resume=True` — automatic turn memory | ✅ Built-in session store |
| OpenAI SDK | Same as Claude SDK — manual `messages[]` management | ❌ In-memory only |
| LangGraph | `MemorySaver` / `SqliteSaver` + `thread_id` | ✅ Persisted — survives restarts |

**Winner for memory: LangGraph** — checkpointing with time-travel is unmatched.

```bash
python 07_memory/claude_sdk.py
python 07_memory/agent_sdk.py
python 07_memory/openai_sdk.py
python 07_memory/langgraph.py
```

---

### UC08 — Sequential Agents
**Concept:** Chain of agents where each agent's output becomes the next agent's input.
Pattern: `Researcher → Analyst → Writer`

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | Three functions called in sequence — manual variable passing |
| Agent SDK | Three `query()` calls in sequence — session continuity optional |
| OpenAI SDK | Three `run_agent()` calls — output string passed as next input |
| LangGraph | `StateGraph` with `PipelineState` — all intermediate outputs captured in state |

**LangGraph advantage:** `PipelineState` holds `research_data`, `analysis_data`, `final_report` — inspect any stage, add checkpointing, swap a node with zero changes to others.

```bash
python 08_sequential_agents/claude_sdk.py
python 08_sequential_agents/agent_sdk.py
python 08_sequential_agents/openai_sdk.py
python 08_sequential_agents/langgraph.py
```

---

### UC09 — Supervisor / Orchestrator
**Concept:** Router LLM classifies the task → dispatches to the right specialist agent.

```
Supervisor → MATH     → Math Agent
           → RESEARCH → Research Agent
           → WRITER   → Writer Agent
           → DATA     → Data Agent
```

| SDK | Key pattern |
|-----|-------------|
| Claude SDK | `supervisor()` → string → `SPECIALIST_MAP[routing](client, task)` |
| Agent SDK | `supervisor_route()` → `quick_query()` with specialist system prompt |
| OpenAI SDK | Same pattern — supervisor call + specialist dispatch dict |
| LangGraph | `supervisor_node` → `conditional_edges` → specialist nodes → **cycle back** to supervisor |

**LangGraph advantage:** Specialists cycle back to supervisor for multi-step tasks. Add checkpointing → entire routing chain is resumable. `create_react_agent()` per specialist gives each a full ReAct loop.

```bash
python 09_supervisor/claude_sdk.py
python 09_supervisor/agent_sdk.py
python 09_supervisor/openai_sdk.py
python 09_supervisor/langgraph.py
```

---

### UC10 — Human-in-the-Loop (HITL)
**Concept:** Pause agent execution at sensitive steps and require human approval before continuing.

| SDK | Mechanism | Persistence |
|-----|-----------|-------------|
| Claude SDK | `if tool_name in SENSITIVE_TOOLS: input()` before `execute_tool()` | ❌ No — loop must stay running |
| Agent SDK | `max_turns=1` + loop manually + `resume=True` for continuation | ✅ Session-level only |
| OpenAI SDK | Same as Claude SDK — manual gate in `tool_calls` loop | ❌ No — loop must stay running |
| LangGraph | `interrupt_before=["node"]` + `MemorySaver` + `app.invoke(None, config)` | ✅ Full — survives restarts |

**Winner for HITL: LangGraph** — only framework where a paused workflow survives server restarts, can wait hours/days for approval, and has full audit trail.

Three LangGraph HITL strategies:
1. `interrupt_before=["sensitive_tools"]` — always pause before a node (declarative)
2. `interrupt_after=["agent"]` — pause after node to review output before continuing
3. `raise NodeInterrupt("msg")` — conditional pause from inside a node

```bash
python 10_human_in_the_loop/claude_sdk.py
python 10_human_in_the_loop/agent_sdk.py
python 10_human_in_the_loop/openai_sdk.py
python 10_human_in_the_loop/langgraph.py
```

---

## Decision Guide — Which SDK to Choose?

### Choose **Claude SDK** (`anthropic`) when:
- You want maximum control over every API call
- You need to fine-tune system prompts per use case
- Your team already knows the Anthropic API
- You're building tool-use agents with custom tools
- Best for: production backends, fine-grained control

### Choose **Claude Agent SDK** (`claude-agent-sdk`) when:
- You want built-in tools (Bash, WebSearch, file ops) without writing tool schemas
- You need session-level memory out of the box
- You're building automation scripts or agentic workflows
- Best for: developer automation, scripting, rapid prototyping

### Choose **OpenAI Python SDK** when:
- You need `response_format=PydanticModel` structured output (cleanest API)
- You want parallel tool calls
- Your team is on OpenAI models
- Best for: data extraction, classification, structured generation

### Choose **LangGraph** when:
- You need multi-agent orchestration (supervisor, pipelines)
- You need human-in-the-loop with persistence
- You need streaming at the node/token level
- You need time-travel debugging or state inspection
- Best for: production multi-agent systems, enterprise workflows

---

## Architecture Pattern Summary

```
Simple tasks:        Claude SDK / OpenAI SDK (direct API call)
Automation:          Claude Agent SDK (built-in tools + sessions)
Structured data:     OpenAI SDK (native Pydantic output)
Multi-agent:         LangGraph (supervisor + specialist graph)
Human approval:      LangGraph (interrupt_before + checkpointer)
Production systems:  LangGraph (full observability + resumability)
```

---

## Shared Utilities

- `shared/tools.py` — mock tool implementations + `ANTHROPIC_TOOLS` / `OPENAI_TOOLS` schemas
- `shared/utils.py` — `load_env()`, `header()`, `require_key()` helpers
- `.env` — `ANTHROPIC_API_KEY` + `OPENAI_API_KEY`
