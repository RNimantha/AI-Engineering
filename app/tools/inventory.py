import sys
from pathlib import Path

# Ensure app/ is on sys.path when this module runs in a subprocess context
_app_dir = str(Path(__file__).parent.parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from claude_agent_sdk import tool

from database import SessionLocal
from inventory_service import InventoryService


@tool("get_inventory", "List all inventory items with their quantities", {})
async def get_inventory(args):
    db = SessionLocal()
    try:
        items = InventoryService(db).get_all_items()
        lines = [f"id={i['id']} sku={i['sku']} name={i['name']} qty={i['quantity']}" for i in items]
        return {"content": [{"type": "text", "text": "\n".join(lines) or "Inventory is empty"}]}
    finally:
        db.close()


@tool("get_item", "Get a single inventory item by name or sku", {"query": str})
async def get_item(args):
    db = SessionLocal()
    try:
        item = InventoryService(db).find_item(args["query"])
        if not item:
            return {
                "content": [{"type": "text", "text": f"Item '{args['query']}' not found"}],
                "is_error": True,
            }
        text = f"id={item.id} sku={item.sku} name={item.name} qty={item.quantity}"
        return {"content": [{"type": "text", "text": text}]}
    finally:
        db.close()


@tool("update_stock", "Update the quantity of an inventory item by name or sku", {"query": str, "quantity": int})
async def update_stock(args):
    db = SessionLocal()
    try:
        result = InventoryService(db).update_stock(args["query"], args["quantity"])
        if result["status"] == "error":
            return {"content": [{"type": "text", "text": result["message"]}], "is_error": True}
        text = f"Updated {result['name']}: {result['old_quantity']} → {result['quantity']}"
        return {"content": [{"type": "text", "text": text}]}
    finally:
        db.close()
