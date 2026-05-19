# Claude Agent SDK - Quick Reference Cheat Sheet

## ⚡ One-Liners

### Simplest Agent Ever
```python
import anyio
from claude_agent_sdk import query

async def main():
    async for msg in query(prompt="What is Python?"):
        print(msg)

anyio.run(main)
```

### Interactive Multi-Turn
```python
from claude_agent_sdk import ClaudeSDKClient
import anyio

async def main():
    async with ClaudeSDKClient() as client:
        await client.query(prompt="First question")
        async for msg in client.receive_response():
            print(msg)
        # Agent remembers context for next query!

anyio.run(main)
```

---

## 🔧 Common Options

### System Prompt (Give Agent a Role)
```python
options = ClaudeAgentOptions(
    system_prompt="You are a Python expert"
)
```

### Control Tools
```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash"],      # Only these
    disallowed_tools=["WebSearch"],                # Never these
)
```

### Limit Turns
```python
options = ClaudeAgentOptions(
    max_turns=5  # Max 5 tool uses
)
```

### Permission Mode
```python
options = ClaudeAgentOptions(
    permission_mode="acceptEdits"  # "manual" = ask user
)
```

### Extended Thinking
```python
options = ClaudeAgentOptions(
    thinking={"type": "enabled", "budget_tokens": 10000}
)
```

### All Together
```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt="You are an expert Python developer",
    allowed_tools=["Read", "Write", "Bash"],
    max_turns=10,
    permission_mode="acceptEdits",
    thinking={"type": "enabled", "budget_tokens": 5000}
)

async for msg in query(prompt="Your prompt", options=options):
    print(msg)
```

---

## 📨 Message Types

### Filter Messages by Type
```python
async for message in query(prompt="..."):
    if message.type == 'text':
        # Agent is talking
        print(f"Agent: {message.content}")
    
    elif message.type == 'tool_use':
        # Agent wants to use a tool
        print(f"Tool: {message.tool}")
        print(f"Args: {message.arguments}")
    
    elif message.type == 'tool_result':
        # Tool result back from execution
        print(f"Result: {message.content}")
    
    elif message.type == 'error':
        # Something went wrong
        print(f"Error: {message.content}")
    
    elif message.type == 'thinking':
        # Claude's internal thoughts (thinking enabled)
        print(f"Thinking: {message.content}")
```

---

## 🛠️ Built-In Tools Reference

### File Operations
```python
# Agent automatically does this:
options = ClaudeAgentOptions(allowed_tools=["Read", "Write", "Edit"])

# Read file → agent uses this
"Please read config.txt"

# Write file → agent uses this  
"Create a file called app.py with..."

# Edit file → agent uses this
"Edit line 5 of config.txt to..."
```

### Bash Commands
```python
options = ClaudeAgentOptions(allowed_tools=["Bash"])

# Agent will run shell commands:
"List all Python files in current directory"
"Run python script.py and show me the output"
"Check the Python version installed"
```

### Search & Find
```python
options = ClaudeAgentOptions(allowed_tools=["Grep", "Glob"])

# Grep - search inside files
"Find all instances of 'TODO' in the codebase"

# Glob - find files by pattern
"Find all .txt files in the data folder"
```

### Web Tools
```python
options = ClaudeAgentOptions(allowed_tools=["WebSearch", "WebFetch"])

# Search web
"Search for Python 3.13 release notes"

# Fetch webpage
"Read the Python docs from python.org"
```

### All Available Tools
```
Read      - Read file contents
Write     - Create/write files
Edit      - Modify existing files
Bash      - Run shell commands
Grep      - Search in files
Glob      - Find files by pattern
WebSearch - Search the internet
WebFetch  - Download web pages
Monitor   - Track long operations
```

---

## 🎯 Custom Tools

### Define a Tool
```python
from claude_agent_sdk import tool

@tool("tool_name", "Short description", {"param1": int, "param2": str})
async def my_tool(args):
    # args['param1'], args['param2']
    return {
        "content": [
            {"type": "text", "text": "Result here"}
        ]
    }
```

### Use Custom Tools
```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeSDKClient

@tool("greet", "Greet someone", {"name": str})
async def greet(args):
    return {"content": [{"type": "text", "text": f"Hello {args['name']}!"}]}

server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=[greet]
)

async with ClaudeSDKClient(mcp_servers=[server]) as client:
    await client.query(prompt="Use the greet tool with name Alice")
    async for msg in client.receive_response():
        print(msg)
```

---

## 📋 `query()` vs `ClaudeSDKClient`

### Use `query()` When:
- Simple, one-off question
- No need for memory
- Don't need interaction
```python
async for msg in query(prompt="What is 2+2?"):
    print(msg)
```

### Use `ClaudeSDKClient` When:
- Multi-turn conversation
- Need to remember context
- Want to build on previous responses
```python
async with ClaudeSDKClient() as client:
    await client.query("First question")
    async for msg in client.receive_response():
        print(msg)
    
    # Ask follow-up - agent remembers!
    await client.query("Follow-up question")
```

---

## 🔗 API Quick Map

### Import Everything You Need
```python
import anyio
from claude_agent_sdk import (
    query,                      # Simple queries
    ClaudeSDKClient,           # Multi-turn
    ClaudeAgentOptions,        # Configuration
    tool,                      # Custom tools
    create_sdk_mcp_server,     # Tool server
)
```

### Run Async Code
```python
# Option 1: anyio
import anyio
anyio.run(your_async_function)

# Option 2: asyncio
import asyncio
asyncio.run(your_async_function)
```

### Common Pattern
```python
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions

async def my_agent():
    options = ClaudeAgentOptions(
        system_prompt="You are helpful",
        allowed_tools=["Read", "Write"],
    )
    
    async for message in query(prompt="Do something", options=options):
        if message.type == 'text':
            print(message.content)

anyio.run(my_agent)
```

---

## 🚀 Common Recipes

### Recipe: Create and Read File
```python
async def file_recipe():
    prompt = """
    1. Create file 'test.txt' with content 'Hello World'
    2. Read the file
    3. Show me the content
    """
    async for msg in query(prompt=prompt):
        if msg.type == 'text':
            print(msg.content)

anyio.run(file_recipe)
```

### Recipe: Run Commands
```python
async def bash_recipe():
    prompt = """
    1. List files in current directory
    2. Count how many Python files there are
    3. Show me one Python file's first 5 lines
    """
    options = ClaudeAgentOptions(allowed_tools=["Bash", "Read"])
    
    async for msg in query(prompt=prompt, options=options):
        if msg.type == 'text':
            print(msg.content)

anyio.run(bash_recipe)
```

### Recipe: Research Something
```python
async def research_recipe():
    prompt = """
    Research 'Python async programming' and:
    1. Search for top 2 results
    2. Read them
    3. Summarize key points
    4. Save to research.md
    """
    options = ClaudeAgentOptions(
        allowed_tools=["WebSearch", "WebFetch", "Write"]
    )
    
    async for msg in query(prompt=prompt, options=options):
        if msg.type == 'text':
            print(msg.content)

anyio.run(research_recipe)
```

### Recipe: Code Review
```python
async def review_recipe(code_str):
    prompt = f"""
    Review this code:
    ```python
    {code_str}
    ```
    
    Find issues and suggest improvements.
    Save improved version to improved.py
    """
    options = ClaudeAgentOptions(
        system_prompt="Expert Python code reviewer",
        allowed_tools=["Write"]
    )
    
    async for msg in query(prompt=prompt, options=options):
        if msg.type == 'text':
            print(msg.content)

anyio.run(review_recipe("def foo():\n  x=1\n  y = 2\n  return x+y"))
```

### Recipe: Interactive Loop
```python
async def interactive_recipe():
    async with ClaudeSDKClient() as client:
        while True:
            user = input("You: ")
            if user.lower() == 'quit':
                break
            
            await client.query(prompt=user)
            async for msg in client.receive_response():
                if msg.type == 'text':
                    print(f"Agent: {msg.content}")

anyio.run(interactive_recipe)
```

---

## ⚙️ Configuration Cheat Sheet

| Option | Values | Example |
|--------|--------|---------|
| `system_prompt` | string | `"You are a Python expert"` |
| `allowed_tools` | list | `["Read", "Write", "Bash"]` |
| `disallowed_tools` | list | `["WebSearch"]` |
| `max_turns` | int | `5` |
| `permission_mode` | string | `"acceptEdits"` (or `"manual"`) |
| `cwd` | path string | `"/home/user/project"` |
| `model` | string | `"claude-opus-4-5"` |
| `max_tokens` | int | `4096` |
| `thinking` | dict | `{"type": "enabled", "budget_tokens": 10000}` |

---

## 🐛 Debugging Tips

### Print Message Details
```python
async for message in query(prompt="..."):
    print(f"Type: {message.type}")
    print(f"Content: {message.content}")
    print(f"Full message: {message}")
    print("---")
```

### Log Tool Usage
```python
async for message in query(prompt="..."):
    if message.type == 'tool_use':
        print(f"⚙️  TOOL: {message.tool}")
        print(f"   ARGS: {message.arguments}")
```

### Catch Errors
```python
try:
    async for message in query(prompt="..."):
        print(message)
except Exception as e:
    print(f"Error: {e}")
```

### Check SDK Version
```python
import claude_agent_sdk
print(claude_agent_sdk.__version__)
```

---

## ✅ Common Patterns Summary

### Pattern 1: Simple Question
```python
async for msg in query(prompt="Your question"):
    if msg.type == 'text': print(msg.content)
```

### Pattern 2: With Tools
```python
opts = ClaudeAgentOptions(allowed_tools=["Read", "Write"])
async for msg in query(prompt="Your prompt", options=opts):
    if msg.type == 'text': print(msg.content)
```

### Pattern 3: Multi-Turn
```python
async with ClaudeSDKClient() as client:
    await client.query("Q1")
    async for msg in client.receive_response():
        print(msg)
    await client.query("Q2")  # Remembers Q1
    async for msg in client.receive_response():
        print(msg)
```

### Pattern 4: Custom Tool
```python
@tool("mytool", "desc", {"arg": int})
async def mytool(args): return {"content": [{"type": "text", "text": "result"}]}
server = create_sdk_mcp_server("name", "1.0.0", tools=[mytool])
async with ClaudeSDKClient(mcp_servers=[server]) as client:
    await client.query("Use mytool")
```

---

## 📚 Official Links

- **Docs**: https://docs.claude.com/en/docs/claude-code/overview
- **API Ref**: https://code.claude.com/docs/en/agent-sdk/python  
- **GitHub**: https://github.com/anthropics/claude-agent-sdk-python
- **PyPI**: https://pypi.org/project/claude-agent-sdk/

---

## 🆘 Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| ImportError | `pip install -U claude-agent-sdk` |
| async/await error | Use `anyio.run()` or `asyncio.run()` |
| Tool not available | Add to `allowed_tools` in options |
| Permission denied | Check `permission_mode` |
| CLI not found | Restart terminal or check PATH |
| Messages not printing | Check `if msg.type == 'text'` filter |

---

## 🎓 Learning Checklist

- [ ] Install `claude-agent-sdk`
- [ ] Run "Hello Agent" example
- [ ] Try with options (system_prompt)
- [ ] Use allowed_tools
- [ ] Test multi-turn with ClaudeSDKClient
- [ ] Create one custom tool
- [ ] Build a real project agent
- [ ] Add error handling
- [ ] Deploy to production (with proper auth)

---

**Keep this handy! 📌**
