"""
Standalone HTTP/SSE MCP server for notes management.

Run separately:  uv run python app/mcp_servers/notes_server.py
Agent connects via McpSSEServerConfig(type="sse", url="http://127.0.0.1:8001/sse")
"""

from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="notes-server",
    host="127.0.0.1",
    port=8001,
)

# In-memory store — resets on server restart
_notes: dict[int, dict] = {}
_next_id = 1


@mcp.tool()
def create_note(title: str, body: str) -> dict:
    """Create a new note with a title and body text."""
    global _next_id
    note = {"id": _next_id, "title": title, "body": body, "created_at": datetime.now().isoformat()}
    _notes[_next_id] = note
    _next_id += 1
    return note


@mcp.tool()
def list_notes() -> list[dict]:
    """List all notes (id, title, created_at)."""
    return [{"id": n["id"], "title": n["title"], "created_at": n["created_at"]} for n in _notes.values()]


@mcp.tool()
def get_note(note_id: int) -> dict:
    """Get full content of a note by id."""
    if note_id not in _notes:
        return {"error": f"Note {note_id} not found"}
    return _notes[note_id]


@mcp.tool()
def delete_note(note_id: int) -> dict:
    """Delete a note by id."""
    if note_id not in _notes:
        return {"error": f"Note {note_id} not found"}
    removed = _notes.pop(note_id)
    return {"deleted": True, "title": removed["title"]}


if __name__ == "__main__":
    print("Notes MCP server starting on http://127.0.0.1:8001/sse")
    mcp.run(transport="sse")
