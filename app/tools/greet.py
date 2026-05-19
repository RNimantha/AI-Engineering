from claude_agent_sdk import tool


@tool("greet", "Greet a person by name", {"name": str})
async def greet_user(args):
    name = args["name"]
    return {
        "content": [{"type": "text", "text": f"Hello, {name}! Nice to meet you!"}]
    }
