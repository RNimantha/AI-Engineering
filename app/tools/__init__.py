from claude_agent_sdk import create_sdk_mcp_server

from .greet import greet_user
from .inventory import get_inventory, get_item, update_stock
from .users import create_user, delete_user, get_all_users, get_user, update_user

all_tools = [
    greet_user,
    get_inventory,
    get_item,
    update_stock,
    get_all_users,
    get_user,
    create_user,
    update_user,
    delete_user,
]

tools_server = create_sdk_mcp_server(
    name="my-tools",
    version="1.0.0",
    tools=all_tools,
)
