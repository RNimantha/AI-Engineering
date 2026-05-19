# Claude Agent SDK for Python - Complete Learning Guide
**Start from Zero Knowledge → Build Production Agents**

---

## 📚 Table of Contents
1. [Concepts & Terminology](#concepts)
2. [Installation & Setup](#installation)
3. [Your First Agent (5 minutes)](#first-agent)
4. [Understanding Messages & Tools](#messages)
5. [Core APIs: `query()` vs `ClaudeSDKClient`](#apis)
6. [Building Custom Tools](#custom-tools)
7. [Advanced Topics](#advanced)
8. [Common Patterns](#patterns)

---

## <a id="concepts"></a>1. Concepts & Terminology

### What is an Agent?
An **agent** is an AI that can:
- 🧠 **Think** - Understand what you ask
- 🔧 **Use Tools** - Take actions (read files, run commands, search web)
- 🔄 **Iterate** - Keep working until done
- 📁 **Access Files** - Read/write your computer
- 🌐 **Search Web** - Fetch information online

**Example**: Instead of just saying "I don't know", an agent can grep your codebase, find the database config, and give you the actual answer.

### Key Differences: Chatbot vs Agent

| Feature | Chatbot | Agent |
|---------|---------|-------|
| Answers questions | ✅ | ✅ |
| **Can run commands** | ❌ | ✅ |
| **Can read files** | ❌ | ✅ |
| **Can search web** | ❌ | ✅ |
| **Can take actions** | ❌ | ✅ |
| **Autonomous** | ❌ | ✅ (with permissions) |

### Built-in Tools Your Agent Can Use
```
Read       - Read files
Write      - Create/write files  
Edit       - Edit existing files
Bash       - Run shell commands
Grep       - Search inside files
Glob       - Find files matching patterns
WebFetch   - Download web content
WebSearch  - Search the internet
Monitor    - Track long-running processes
```

---

## <a id="installation"></a>2. Installation & Setup

### Step 1: Prerequisites
```bash
# Python 3.10 or higher
python --version  # Should be 3.10+

# Node.js (for Claude Code CLI)
node --version    # Should be v18+
```

### Step 2: Install Claude Agent SDK
```bash
pip install claude-agent-sdk
```

### Step 3: Verify Installation
```python
from claude_agent_sdk import query
print("✅ Claude Agent SDK installed successfully!")
```

### Step 4: Set Your API Key (If needed)
```bash
# The SDK uses Claude Code CLI which handles auth
# But for programmatic use, you may need:
export ANTHROPIC_API_KEY="your-api-key-here"
```

---

## <a id="first-agent"></a>3. Your First Agent (5 minutes)

### Most Basic Example
```python
import anyio
from claude_agent_sdk import query

async def main():
    # Ask the agent a simple question
    async for message in query(prompt="What is 2 + 2?"):
        print(f"Agent: {message}")

anyio.run(main)
```

**Run it:**
```bash
python script.py
```

### Understanding the Output
```
Message(type='text', content='The answer is 4.')
Message(type='tool_use', tool='bash', arguments={'command': 'echo 4'})
Message(type='tool_result', content='4')
Message(type='text', content='Done!')
```

Each message type tells you what the agent is doing:
- `text` - Agent is thinking/responding
- `tool_use` - Agent wants to use a tool
- `tool_result` - Result from a tool
- `error` - Something went wrong

---

## <a id="messages"></a>4. Understanding Messages & Tools

### Message Structure
Every response from the agent is a `Message` object:

```python
async for message in query(prompt="List files in current directory"):
    print(f"Type: {message.type}")
    print(f"Content: {message.content}")
```

### Message Types You'll See

```python
# 1. TEXT MESSAGE - Agent is thinking/talking
if message.type == 'text':
    print(f"Agent says: {message.content}")

# 2. TOOL USE - Agent wants to use a tool
if message.type == 'tool_use':
    print(f"Agent wants to use: {message.tool}")
    print(f"Arguments: {message.arguments}")

# 3. TOOL RESULT - Result from running a tool
if message.type == 'tool_result':
    print(f"Tool returned: {message.content}")

# 4. ERROR - Something failed
if message.type == 'error':
    print(f"Error: {message.content}")
```

### Real Example: Listing Files
```python
import anyio
from claude_agent_sdk import query

async def main():
    prompt = "List all Python files (.py) in the current directory"
    
    async for message in query(prompt=prompt):
        if message.type == 'text':
            print(f"✏️  Agent: {message.content}")
        elif message.type == 'tool_use':
            print(f"🔧 Using tool: {message.tool}")
        elif message.type == 'tool_result':
            print(f"📊 Result: {message.content}")

anyio.run(main)
```

---

## <a id="apis"></a>5. Core APIs: `query()` vs `ClaudeSDKClient`

### Option 1: `query()` - For Simple, One-Off Tasks

**When to use:**
- Simple questions
- Single-turn interactions
- Batch tasks
- No need to remember conversation

**Example:**
```python
from claude_agent_sdk import query

async def main():
    async for message in query(prompt="Create a hello.py file"):
        print(message)

anyio.run(main)
```

### Option 2: `ClaudeSDKClient` - For Multi-Turn Conversations

**When to use:**
- Back-and-forth conversations
- Need to build on previous context
- Interactive applications
- Real-time interaction

**Example:**
```python
import anyio
from claude_agent_sdk import ClaudeSDKClient

async def main():
    # Create a session
    async with ClaudeSDKClient() as client:
        
        # Turn 1: Ask something
        print("Turn 1: Asking agent to analyze code...")
        await client.query(prompt="Look at hello.py and tell me what it does")
        
        # Get responses
        async for message in client.receive_response():
            print(f"Response: {message}")
        
        # Turn 2: Follow-up question (agent remembers Turn 1)
        print("\nTurn 2: Follow-up question...")
        await client.query(prompt="Now modify it to also print the current time")
        
        async for message in client.receive_response():
            print(f"Response: {message}")

anyio.run(main)
```

### Comparison Table

| Feature | `query()` | `ClaudeSDKClient` |
|---------|-----------|-------------------|
| Simple one-off | ✅ Great | ⚠️ Overkill |
| Multi-turn | ❌ No | ✅ Perfect |
| Conversation memory | ❌ No | ✅ Yes |
| Custom tools | ❌ No | ✅ Yes |
| Hooks | ❌ No | ✅ Yes |
| Complexity | Simple | Medium |

---

## <a id="custom-tools"></a>6. Building Custom Tools

### What are Custom Tools?
Tools that YOU define. Instead of using only built-in tools (bash, read, write), you can:
- Call your own Python functions
- Query databases
- Call APIs
- Do custom calculations

### Simple Custom Tool Example

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeSDKClient
import anyio

# Step 1: Define a tool with @tool decorator
@tool("greet", "Greet a person by name", {"name": str})
async def greet_user(args):
    """A simple greeting tool"""
    name = args['name']
    return {
        "content": [
            {"type": "text", "text": f"Hello, {name}! Nice to meet you!"}
        ]
    }

# Step 2: Create an MCP server with your tools
server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet_user]
)

# Step 3: Use it with Claude
async def main():
    async with ClaudeSDKClient(mcp_servers=[server]) as client:
        await client.query(prompt="Use the greet tool to greet 'Alice'")
        
        async for message in client.receive_response():
            if message.type == 'text':
                print(f"Agent: {message.content}")
            elif message.type == 'tool_use':
                print(f"Using tool: {message.tool}")

anyio.run(main)
```

### More Complex Tool: Database Query

```python
@tool("query_database", "Query user database", {
    "user_id": int,
    "fields": list  # e.g., ["name", "email"]
})
async def query_db(args):
    """Query your database"""
    user_id = args['user_id']
    fields = args['fields']
    
    # Simulate a database lookup
    users = {
        1: {"name": "Alice", "email": "alice@example.com", "role": "admin"},
        2: {"name": "Bob", "email": "bob@example.com", "role": "user"},
    }
    
    if user_id not in users:
        return {"content": [{"type": "text", "text": f"User {user_id} not found"}]}
    
    user = users[user_id]
    result = {field: user.get(field, "N/A") for field in fields}
    
    return {
        "content": [
            {"type": "text", "text": str(result)}
        ]
    }
```

---

## <a id="advanced"></a>7. Advanced Topics

### 7.1 Controlling Tool Access with Permissions

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        # Only allow these tools
        allowed_tools=["Read", "Write"],
        # Block these specific tools
        disallowed_tools=["Bash"],
        # Max number of turns (tool uses)
        max_turns=5,
        # Ask for permission before using tools
        permission_mode="manual",  # or "acceptEdits", "auto"
    )
    
    async for message in query(prompt="Your prompt here", options=options):
        print(message)

anyio.run(main)
```

### 7.2 Using Hooks for Automation

Hooks let you automatically respond to the agent without user input:

```python
from claude_agent_sdk import ClaudeSDKClient, Hook

# Define a hook
async def auto_approve_hook(context):
    """Automatically approve certain actions"""
    if context.tool_name == "Read":
        # Auto-approve reading files
        return True
    elif context.tool_name == "Write":
        # Ask user before writing
        user_input = input(f"Write to {context.arguments.get('path')}? (y/n): ")
        return user_input.lower() == 'y'
    return False

async def main():
    async with ClaudeSDKClient(hooks=[auto_approve_hook]) as client:
        await client.query(prompt="Read hello.py")
        async for message in client.receive_response():
            print(message)

anyio.run(main)
```

### 7.3 Extended Thinking (Deep Reasoning)

Make Claude think deeply before acting:

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        thinking={
            "type": "enabled",
            "budget_tokens": 10000  # Give it thinking budget
        }
    )
    
    async for message in query(
        prompt="Debug this complex issue...",
        options=options
    ):
        if message.type == 'thinking':
            print(f"🤔 Agent thinking: {message.content[:100]}...")
        elif message.type == 'text':
            print(f"✅ Result: {message.content}")

anyio.run(main)
```

### 7.4 System Prompts & Configuration

```python
from claude_agent_sdk import ClaudeAgentOptions, query

async def main():
    options = ClaudeAgentOptions(
        # Set the agent's personality/role
        system_prompt="""You are an expert Python developer.
        When asked to write code, always:
        1. Add type hints
        2. Add docstrings
        3. Follow PEP 8
        """,
        
        # Set working directory
        cwd="/home/user/project",
        
        # Use specific Claude model
        model="claude-opus-4-5",
        
        # Set max tokens for response
        max_tokens=4096,
    )
    
    async for message in query(
        prompt="Write a Python function to...",
        options=options
    ):
        print(message)

anyio.run(main)
```

---

## <a id="patterns"></a>8. Common Patterns & Use Cases

### Pattern 1: File Processing Agent
```python
async def process_files_agent():
    """Agent that processes multiple files"""
    prompt = """
    1. Find all .txt files in the data/ directory
    2. Read each file
    3. Count the lines in each
    4. Write a summary to summary.txt
    """
    
    options = ClaudeAgentOptions(
        allowed_tools=["Glob", "Read", "Write"],
        system_prompt="You are a file processing specialist"
    )
    
    async for message in query(prompt=prompt, options=options):
        if message.type == 'text':
            print(f"Status: {message.content}")
```

### Pattern 2: Code Analysis Agent
```python
async def code_analyzer():
    """Agent that analyzes and improves code"""
    prompt = """
    Analyze the file main.py and:
    1. Identify any bugs
    2. Check for performance issues
    3. Suggest improvements
    4. Create an improved version
    """
    
    options = ClaudeAgentOptions(
        system_prompt="""You are an expert code reviewer. 
        Be thorough but constructive in your feedback.""",
        allowed_tools=["Read", "Write"],
        max_turns=10
    )
    
    async for message in query(prompt=prompt, options=options):
        print(message)
```

### Pattern 3: Research Agent
```python
async def research_agent():
    """Agent that researches topics on the web"""
    prompt = """
    Research the latest developments in quantum computing and:
    1. Find 3 recent articles
    2. Summarize the key findings
    3. Save the summary to research.md
    """
    
    options = ClaudeAgentOptions(
        allowed_tools=["WebSearch", "WebFetch", "Write"],
        system_prompt="You are a thorough researcher"
    )
    
    async for message in query(prompt=prompt, options=options):
        print(message)
```

### Pattern 4: Multi-Turn Conversation
```python
async def interactive_session():
    """Interactive agent conversation"""
    async with ClaudeSDKClient() as client:
        print("Starting interactive session. Type 'quit' to exit.\n")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'quit':
                break
            
            await client.query(prompt=user_input)
            
            async for message in client.receive_response():
                if message.type == 'text':
                    print(f"Agent: {message.content}\n")
```

---

## 🎯 Learning Path Summary

1. **Day 1**: Install SDK → Run first agent → Understand messages
2. **Day 2**: Learn `query()` vs `ClaudeSDKClient` → Try multi-turn
3. **Day 3**: Add options → Control permissions → System prompts
4. **Day 4**: Build custom tools → MCP basics
5. **Day 5**: Combine everything → Build a real project

---

## 📚 Official Resources

- **Agent SDK Docs**: https://docs.claude.com/en/docs/claude-code/overview
- **Python Reference**: https://code.claude.com/docs/en/agent-sdk/python
- **GitHub Examples**: https://github.com/anthropics/claude-agent-sdk-python
- **Blog Guide**: https://www.eesel.ai/blog/python-claude-code-sdk

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Import error | `pip install --upgrade claude-agent-sdk` |
| async/await error | Use `anyio.run()` or `asyncio.run()` |
| Tool not found | Check `allowed_tools` in options |
| CLI not found | SDK auto-installs it, restart terminal |
| Permission denied | Check `permission_mode` setting |

---

**Happy building! 🚀**
