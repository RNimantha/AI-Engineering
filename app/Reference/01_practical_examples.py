"""
Claude Agent SDK - Practical Runnable Examples
Level: Beginner to Intermediate
Copy each example and run: python example_name.py
"""

# ============================================================================
# EXAMPLE 1: HELLO AGENT - Your First Agent (EASIEST)
# ============================================================================

"""
1_hello_agent.py - The absolute simplest agent

Run this:
    python 1_hello_agent.py

What it does:
    - Asks the agent a simple question
    - Prints all responses
"""

import anyio
from claude_agent_sdk import query

async def hello_agent():
    """Simplest possible agent example"""
    
    # Ask the agent something
    prompt = "What are the top 3 programming languages in 2025?"
    
    print(f"🤖 Asking agent: {prompt}\n")
    
    # Get responses
    async for message in query(prompt=prompt):
        print(f"📨 Message type: {message.type}")
        print(f"   Content: {message.content}\n")

# Run it
# anyio.run(hello_agent)


# ============================================================================
# EXAMPLE 2: FILE OPERATIONS - Read and Write Files
# ============================================================================

"""
2_file_operations.py - Agent working with files

What it does:
    - Creates a file
    - Reads the file
    - Modifies the file
"""

async def file_operations_agent():
    """Agent that manipulates files"""
    
    # Tell the agent to create a file
    prompt = """
    1. Create a file called 'my_config.txt' with these contents:
       NAME=MyApp
       VERSION=1.0
       DEBUG=true
    
    2. Read the file to confirm it was created
    3. Tell me what you see
    """
    
    print("📁 Starting file operations agent...\n")
    
    async for message in query(prompt=prompt):
        if message.type == 'text':
            print(f"✅ Agent says: {message.content}\n")
        elif message.type == 'tool_use':
            print(f"🔧 Agent using tool: {message.tool}")

# Run it
# anyio.run(file_operations_agent)


# ============================================================================
# EXAMPLE 3: BASH COMMANDS - Run Shell Commands
# ============================================================================

"""
3_bash_commands.py - Agent running system commands

What it does:
    - Lists files in directory
    - Runs a Python script
    - Checks system info
"""

async def bash_agent():
    """Agent that runs bash commands"""
    
    prompt = """
    1. List all Python files (.py) in the current directory
    2. Count how many files there are
    3. Show me the file sizes
    """
    
    print("💻 Running bash agent...\n")
    
    async for message in query(prompt=prompt):
        if message.type == 'text':
            print(f"📊 Agent found: {message.content}\n")
        elif message.type == 'tool_use':
            print(f"🔧 Running: {message.tool}")

# Run it
# anyio.run(bash_agent)


# ============================================================================
# EXAMPLE 4: OPTIONS & CONFIGURATION - Control Agent Behavior
# ============================================================================

"""
4_configured_agent.py - Using options to control the agent

What it does:
    - Sets a custom system prompt
    - Limits which tools can be used
    - Adds other configurations
"""

from claude_agent_sdk import ClaudeAgentOptions

async def configured_agent():
    """Agent with custom configuration"""
    
    # Create options
    options = ClaudeAgentOptions(
        # Give the agent a role
        system_prompt="""You are a Python expert assistant.
        Always write clean, well-documented code.
        Follow PEP 8 standards.
        Add type hints to all functions.""",
        
        # Only allow these tools
        allowed_tools=["Read", "Write", "Bash"],
        
        # Don't allow this tool
        disallowed_tools=["WebSearch"],
        
        # Maximum number of tool uses
        max_turns=5,
    )
    
    prompt = "Create a simple Python script that calculates Fibonacci numbers"
    
    print("⚙️  Starting configured agent...\n")
    
    async for message in query(prompt=prompt, options=options):
        if message.type == 'text':
            print(f"✅ {message.content}\n")

# Run it
# anyio.run(configured_agent)


# ============================================================================
# EXAMPLE 5: MULTI-TURN CONVERSATION - Remember Context
# ============================================================================

"""
5_multi_turn.py - Two-way conversation with memory

What it does:
    - Asks agent a question
    - Asks a follow-up based on the response
    - Agent remembers the context
"""

from claude_agent_sdk import ClaudeSDKClient

async def multi_turn_conversation():
    """Multi-turn conversation with context memory"""
    
    print("💬 Starting multi-turn conversation...\n")
    
    # Create a session that remembers context
    async with ClaudeSDKClient() as client:
        
        # TURN 1: Create a file
        print("Turn 1️⃣  Creating a file...")
        await client.query(prompt="Create a file called 'story.txt' with a short poem about Python programming")
        
        # Receive responses for Turn 1
        async for message in client.receive_response():
            if message.type == 'text':
                print(f"   Agent: {message.content}\n")
        
        # TURN 2: Follow-up (agent remembers the file!)
        print("Turn 2️⃣  Follow-up question...")
        await client.query(prompt="Now read the file you just created and add one more line at the end. Make it about code quality.")
        
        # Receive responses for Turn 2
        async for message in client.receive_response():
            if message.type == 'text':
                print(f"   Agent: {message.content}\n")
        
        # TURN 3: Another follow-up
        print("Turn 3️⃣  Another follow-up...")
        await client.query(prompt="Read the file one more time and tell me the total number of lines")
        
        async for message in client.receive_response():
            if message.type == 'text':
                print(f"   Agent: {message.content}\n")

# Run it
# anyio.run(multi_turn_conversation)


# ============================================================================
# EXAMPLE 6: CUSTOM TOOLS - Define Your Own Tools
# ============================================================================

"""
6_custom_tools.py - Create tools that the agent can use

What it does:
    - Define a custom calculator tool
    - Define a custom greeting tool
    - Agent uses them when needed
"""

from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeSDKClient

# Define custom tools with @tool decorator
@tool("add_numbers", "Add two numbers together", {"a": int, "b": int})
async def add_numbers(args):
    """A simple addition tool"""
    result = args['a'] + args['b']
    return {
        "content": [
            {"type": "text", "text": f"{args['a']} + {args['b']} = {result}"}
        ]
    }

@tool("multiply_numbers", "Multiply two numbers", {"x": int, "y": int})
async def multiply_numbers(args):
    """A simple multiplication tool"""
    result = args['x'] * args['y']
    return {
        "content": [
            {"type": "text", "text": f"{args['x']} × {args['y']} = {result}"}
        ]
    }

async def custom_tools_agent():
    """Agent with custom tools"""
    
    # Create a server with your custom tools
    server = create_sdk_mcp_server(
        name="math-tools",
        version="1.0.0",
        tools=[add_numbers, multiply_numbers]
    )
    
    print("🧮 Starting custom tools agent...\n")
    
    # Use the server with an agent
    async with ClaudeSDKClient(mcp_servers=[server]) as client:
        
        # Ask agent to use the tools
        prompt = "Use the tools to: Add 5 and 3, then multiply the result by 2"
        
        await client.query(prompt=prompt)
        
        async for message in client.receive_response():
            if message.type == 'text':
                print(f"✅ {message.content}")
            elif message.type == 'tool_use':
                print(f"🔧 Using tool: {message.tool}")

# Run it
# anyio.run(custom_tools_agent)


# ============================================================================
# EXAMPLE 7: WEB SEARCH - Research on the Internet
# ============================================================================

"""
7_web_search.py - Agent searches the web and fetches information

What it does:
    - Searches for recent information
    - Reads web pages
    - Summarizes findings
"""

async def web_search_agent():
    """Agent that searches the web"""
    
    prompt = """
    Research the topic "artificial intelligence trends 2025" and:
    1. Search for the top 3 results
    2. Read at least 2 of them
    3. Summarize the key trends you found
    4. Save the summary to ai_trends_2025.md
    """
    
    options = ClaudeAgentOptions(
        allowed_tools=["WebSearch", "WebFetch", "Write"],
        system_prompt="You are a research specialist. Be thorough and cite your sources."
    )
    
    print("🔍 Starting web search agent...\n")
    
    async for message in query(prompt=prompt, options=options):
        if message.type == 'text':
            print(f"📰 {message.content[:200]}...")

# Run it
# anyio.run(web_search_agent)


# ============================================================================
# EXAMPLE 8: ERROR HANDLING - Handle Failures Gracefully
# ============================================================================

"""
8_error_handling.py - Handle errors that agents encounter

What it does:
    - Catches errors from tool execution
    - Prints error messages
    - Agent recovers and continues
"""

async def error_handling_agent():
    """Agent with error handling"""
    
    prompt = """
    Try to:
    1. Read a file that doesn't exist (this will fail)
    2. Create the file with some content
    3. Read it successfully
    """
    
    print("⚠️  Starting error handling demo...\n")
    
    try:
        async for message in query(prompt=prompt):
            if message.type == 'error':
                print(f"❌ Error occurred: {message.content}")
            elif message.type == 'text':
                print(f"✅ {message.content}")
            elif message.type == 'tool_result':
                print(f"📊 Result: {message.content}")
                
    except Exception as e:
        print(f"Exception caught: {e}")

# Run it
# anyio.run(error_handling_agent)


# ============================================================================
# EXAMPLE 9: REAL-WORLD USE CASE - Code Review Agent
# ============================================================================

"""
9_code_review_agent.py - Agent that reviews code for quality

What it does:
    - Reads your code files
    - Analyzes them
    - Provides improvements
    - Saves suggestions
"""

async def code_review_agent():
    """Agent that reviews code quality"""
    
    # First, create a sample Python file with some issues
    sample_code = '''def calculate(x,y):
    result = x+y
    print(result)
    return result

def process_data(data):
    for i in data:
        print(i)
    return data
'''
    
    prompt = f"""
    Review this Python code for quality:
    
    ```python
    {sample_code}
    ```
    
    Please:
    1. Identify any issues (style, performance, etc.)
    2. Suggest improvements
    3. Provide a corrected version
    4. Save the improved code to improved_code.py
    """
    
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python code reviewer",
        allowed_tools=["Write"],
    )
    
    print("🔍 Starting code review agent...\n")
    
    async for message in query(prompt=prompt, options=options):
        if message.type == 'text':
            print(f"📝 {message.content}\n")

# Run it
# anyio.run(code_review_agent)


# ============================================================================
# EXAMPLE 10: FULL WORKFLOW - Complete Project Automation
# ============================================================================

"""
10_project_automation.py - Comprehensive project setup agent

What it does:
    - Creates project structure
    - Initializes files
    - Sets up configuration
    - Creates documentation
"""

async def project_setup_agent():
    """Automate project setup"""
    
    prompt = """
    Set up a new Python project with this structure:
    
    myproject/
    ├── src/
    │   ├── __init__.py
    │   └── main.py
    ├── tests/
    │   └── test_main.py
    ├── README.md
    └── requirements.txt
    
    Do:
    1. Create all directories and files
    2. Add starter code to main.py (a simple function)
    3. Add a test example to test_main.py
    4. Create README.md with project description
    5. Add common requirements to requirements.txt
    """
    
    options = ClaudeAgentOptions(
        system_prompt="You are a project initialization expert",
        allowed_tools=["Write", "Bash"],
        max_turns=10,
    )
    
    print("📦 Setting up new project...\n")
    
    async for message in query(prompt=prompt, options=options):
        if message.type == 'text':
            print(f"✅ {message.content}\n")

# Run it
# anyio.run(project_setup_agent)


# ============================================================================
# TEMPLATE: Use This to Create Your Own
# ============================================================================

"""
template_custom_agent.py - Template for building your own agent

Copy this and modify the prompt for your needs!
"""

async def my_custom_agent():
    """Your custom agent template"""
    
    # CUSTOMIZE THIS:
    prompt = "Replace this with what you want the agent to do"
    
    # CUSTOMIZE OPTIONS (optional):
    options = ClaudeAgentOptions(
        system_prompt="Replace with agent role/personality",
        allowed_tools=["Read", "Write", "Bash"],  # Choose tools you need
        max_turns=10,
    )
    
    print("🤖 Starting my custom agent...\n")
    
    async for message in query(prompt=prompt, options=options):
        # Handle different message types
        if message.type == 'text':
            print(f"✅ Agent: {message.content}")
        elif message.type == 'tool_use':
            print(f"🔧 Using: {message.tool}")
        elif message.type == 'tool_result':
            print(f"📊 Result: {message.content}")
        elif message.type == 'error':
            print(f"❌ Error: {message.content}")

# Run it
# anyio.run(my_custom_agent)


# ============================================================================
# HOW TO RUN THESE EXAMPLES
# ============================================================================

"""
1. Copy one example function (e.g., hello_agent)

2. Create a new file: example1.py

3. Paste the imports and the example:
   ```
   import anyio
   from claude_agent_sdk import query
   
   async def hello_agent():
       # ... code ...
   
   if __name__ == "__main__":
       anyio.run(hello_agent)
   ```

4. Run it:
   python example1.py

5. Watch the agent work! 🎉
"""

# ============================================================================
# QUICK REFERENCE: Message Types
# ============================================================================

"""
When you iterate through agent responses, you'll see different types:

message.type == 'text'
    → Agent is thinking or providing information
    → Print it to show user

message.type == 'tool_use'
    → Agent wants to use a tool (Read, Write, Bash, etc.)
    → Shows what tool and what arguments

message.type == 'tool_result'
    → Result from running a tool
    → Contains the output of the tool

message.type == 'error'
    → Something went wrong
    → Contains error message

message.type == 'thinking'
    → Claude's internal thoughts (when thinking enabled)
    → Useful for debugging

Example iteration:
    async for message in query(prompt="Your prompt"):
        if message.type == 'text':
            print(f"Agent: {message.content}")
        elif message.type == 'tool_use':
            print(f"Tool: {message.tool} | Args: {message.arguments}")
        elif message.type == 'error':
            print(f"Error: {message.content}")
"""
