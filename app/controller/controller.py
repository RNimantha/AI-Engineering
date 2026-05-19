"""
FastAPI controller with MySQL persistence for the Claude Agent SDK demo.

Drop-in replacement for app/controller/controller.py.  All existing
endpoints are preserved with identical request/response contracts so the
React frontend requires zero changes.

New behaviour vs the original controller:
  - Conversations, messages and tool-call events are written to MySQL.
  - Sessions are tied to a user row via the optional X-Session-ID header.
    The frontend can start sending  localStorage.getItem('sessionId')  as
    that header to get persistent, per-user history; if the header is
    absent the endpoint still works (uses a per-request anonymous session).
  - /api/conversations, /api/inventory and /api/notes endpoints are added
    without breaking the original /api/health and /api/chat routes.

Place this file at: app/controller/controller.py
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from database import get_db
from inventory_service import InventoryService
from models import AuditLog, Conversation, InventoryItem, Message, ToolCall, User, UserNote

# The agent service is imported from the existing agents module — unchanged.
from agent.agents import ClaudeAgentService

logger = logging.getLogger(__name__)

# Singleton agent service (stateless; safe to share across requests)
_agent_service = ClaudeAgentService()

app = FastAPI(title="ClaudeSDK Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic request/response models ──────────────────────────────────────────

class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    """Identical to the original — frontend sends {"messages": [...]}."""
    messages: list[ChatTurn] = Field(min_length=1)


# ── Session / user helpers ─────────────────────────────────────────────────────

def _resolve_session_id(x_session_id: Optional[str]) -> str:
    """
    Return the session ID from the request header, or generate a throwaway
    UUID for requests that do not include the header (original frontend).
    """
    return x_session_id.strip() if x_session_id else str(uuid.uuid4())


def _get_or_create_user(db: Session, session_id: str) -> User:
    """
    Look up a User by session_id; create one if not found.
    In production replace this with real authentication.
    """
    user = db.query(User).filter(User.session_id == session_id).first()
    if not user:
        user = User(
            username=f"user_{session_id[:8]}",
            session_id=session_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created user %d for session %s", user.id, session_id[:8])
    return user


def _get_or_create_conversation(
    db: Session,
    user: User,
    messages: list[dict],
    conversation_id: Optional[int] = None,
) -> Conversation:
    """
    Return an existing conversation or create a new one.

    Matching heuristic (no conversation_id supplied):
      - Find the most-recently-updated non-archived conversation for this user.
      - If the number of stored messages is one fewer than the incoming list
        (i.e. the last user message is new), it's a continuation.
      - Otherwise start a fresh conversation.
    """
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv

    # Try to match to the user's most recent open conversation
    latest = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id, Conversation.is_archived == False)  # noqa: E712
        .order_by(desc(Conversation.updated_at))
        .first()
    )
    if latest:
        stored_count = db.query(Message).filter(Message.conversation_id == latest.id).count()
        incoming_count = len(messages)
        # The frontend sends the full history; the last entry is the new user turn.
        # If stored == incoming - 1 this is a continuation of the same thread.
        if stored_count == incoming_count - 1:
            return latest

    # New conversation — use the first user message as the title
    first_user = next((m for m in messages if m["role"] == "user"), None)
    title = (first_user["content"][:80] if first_user else "New Conversation")
    conv = Conversation(user_id=user.id, title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    _log_audit(db, user.id, "create_conversation", "conversation", conv.id)
    return conv


def _log_audit(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> None:
    """Append a row to audit_logs.  Silently swallows errors so it never breaks the main flow."""
    try:
        db.add(AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        ))
        db.commit()
    except Exception as exc:
        logger.warning("audit_log write failed (non-fatal): %s", exc)
        db.rollback()


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health(db: Session = Depends(get_db)) -> dict:
    """Check API liveness and database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        logger.error("Health check DB error: %s", exc)
        db_status = f"error: {exc}"
    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Chat (main streaming endpoint) ────────────────────────────────────────────

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Main chat endpoint — identical contract to the original controller.

    Request body:  {"messages": [{"role": "user"|"assistant", "content": "..."}]}
    Optional header: X-Session-ID: <uuid>   (enables persistent history)

    SSE stream format:
        data: {"type": "assistant", "content": "..."}\n\n   — text chunk
        data: {"type": "tool",      "content": "..."}\n\n   — tool name
        data: {"type": "result",    "content": "..."}\n\n   — agent result subtype
        data: [DONE]\n\n                                    — stream end
    """
    session_id = _resolve_session_id(x_session_id)
    messages = [m.model_dump() for m in request.messages]

    # Resolve user and conversation synchronously before starting the stream.
    # (SQLAlchemy sync ops must not run inside the async generator body.)
    user = _get_or_create_user(db, session_id)
    conversation = _get_or_create_conversation(db, user, messages)

    # Persist the new user message (last entry in the messages list).
    last_turn = messages[-1]
    user_msg = Message(
        conversation_id=conversation.id,
        role=last_turn["role"],
        content=last_turn["content"],
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Create a placeholder assistant message row; content filled after stream.
    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content="",
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    assistant_msg_id = assistant_msg.id
    conversation_id = conversation.id

    async def event_generator():
        """
        Wraps ClaudeAgentService.stream() and tees events to:
          1. The SSE response (frontend)
          2. MySQL (messages + tool_calls tables)

        A new db session is opened here so the generator owns its own
        connection and is not racing with the outer request session.
        """
        from database import SessionLocal

        gen_db = SessionLocal()
        full_response: list[str] = []
        tool_names: list[str] = []

        try:
            async for event in _agent_service.stream(messages):
                payload = json.dumps({"type": event.type, "content": event.content})
                yield f"data: {payload}\n\n"

                if event.type == "assistant" and event.content:
                    full_response.append(event.content)
                elif event.type == "tool" and event.content:
                    tool_names.append(event.content)
                    # Record tool invocation immediately for real-time visibility
                    tc = ToolCall(
                        message_id=assistant_msg_id,
                        tool_name=event.content,
                        tool_input={},   # not available at stream level
                        status="triggered",
                    )
                    gen_db.add(tc)
                    gen_db.commit()

            # Persist completed assistant text
            final_content = "\n\n".join(full_response)
            gen_db.query(Message).filter(Message.id == assistant_msg_id).update(
                {"content": final_content}
            )
            # Bump conversation.updated_at
            gen_db.query(Conversation).filter(Conversation.id == conversation_id).update(
                {"updated_at": datetime.utcnow()}
            )
            gen_db.commit()
            logger.info(
                "conv=%d msgs saved, tools=%s", conversation_id, tool_names or "none"
            )

        except Exception as exc:
            logger.error("Stream error: %s", exc, exc_info=True)
            error_payload = json.dumps({"type": "error", "content": str(exc)})
            yield f"data: {error_payload}\n\n"
        finally:
            gen_db.close()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Conversation management ────────────────────────────────────────────────────

@app.get("/api/conversations")
async def list_conversations(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """List all non-archived conversations for the session user, newest first."""
    user = _get_or_create_user(db, x_session_id)
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id, Conversation.is_archived == False)  # noqa: E712
        .order_by(desc(Conversation.updated_at))
        .all()
    )
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
                "message_count": db.query(Message).filter(Message.conversation_id == c.id).count(),
            }
            for c in convs
        ]
    }


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Return full message + tool-call history for a conversation."""
    user = _get_or_create_user(db, x_session_id)
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "tool_calls": [
                    {
                        "id": tc.id,
                        "tool_name": tc.tool_name,
                        "status": tc.status,
                        "created_at": tc.created_at.isoformat(),
                    }
                    for tc in m.tool_calls
                ],
            }
            for m in conv.messages
        ],
    }


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Soft-delete (archive) a conversation."""
    user = _get_or_create_user(db, x_session_id)
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.is_archived = True
    db.commit()
    _log_audit(db, user.id, "archive_conversation", "conversation", conversation_id)
    return {"status": "archived"}


# ── Inventory ──────────────────────────────────────────────────────────────────

@app.get("/api/inventory")
async def get_inventory(db: Session = Depends(get_db)):
    """Return all inventory items."""
    return {"inventory": InventoryService(db).get_all_items()}


@app.post("/api/inventory")
async def upsert_inventory_item(
    item: dict,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Create a new inventory item or update quantity/price if sku already exists."""
    session_id = _resolve_session_id(x_session_id)
    user = _get_or_create_user(db, session_id)

    sku = item.get("sku", "").strip()
    if not sku:
        raise HTTPException(status_code=422, detail="sku is required")

    return InventoryService(db).upsert_item(
        sku=sku,
        name=item.get("name"),
        quantity=item.get("quantity"),
        price=item.get("price"),
        description=item.get("description"),
        user_id=user.id,
    )


# ── Notes ──────────────────────────────────────────────────────────────────────

@app.get("/api/notes")
async def get_notes(
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Return all notes for the session user, pinned notes first."""
    user = _get_or_create_user(db, x_session_id)
    notes = (
        db.query(UserNote)
        .filter(UserNote.user_id == user.id)
        .order_by(desc(UserNote.is_pinned), desc(UserNote.updated_at))
        .all()
    )
    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "is_pinned": n.is_pinned,
                "created_at": n.created_at.isoformat(),
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]
    }


@app.post("/api/notes")
async def create_note(
    note: dict,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Create a persistent note (survives server restarts)."""
    user = _get_or_create_user(db, x_session_id)
    new_note = UserNote(
        user_id=user.id,
        title=note.get("title", "Untitled"),
        content=note.get("content", ""),
        is_pinned=note.get("is_pinned", False),
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    _log_audit(db, user.id, "create_note", "note", new_note.id)
    return {
        "status": "created",
        "note": {
            "id": new_note.id,
            "title": new_note.title,
            "content": new_note.content,
            "created_at": new_note.created_at.isoformat(),
        },
    }


@app.put("/api/notes/{note_id}")
async def update_note(
    note_id: int,
    note: dict,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Update title, content, or pinned status of an existing note."""
    user = _get_or_create_user(db, x_session_id)
    db_note = db.query(UserNote).filter(
        UserNote.id == note_id, UserNote.user_id == user.id
    ).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    if "title" in note:
        db_note.title = note["title"]
    if "content" in note:
        db_note.content = note["content"]
    if "is_pinned" in note:
        db_note.is_pinned = note["is_pinned"]
    db_note.updated_at = datetime.utcnow()
    db.commit()
    _log_audit(db, user.id, "update_note", "note", note_id)
    return {"status": "updated"}


@app.delete("/api/notes/{note_id}")
async def delete_note(
    note_id: int,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    db: Session = Depends(get_db),
):
    """Permanently delete a note."""
    user = _get_or_create_user(db, x_session_id)
    db_note = db.query(UserNote).filter(
        UserNote.id == note_id, UserNote.user_id == user.id
    ).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(db_note)
    db.commit()
    _log_audit(db, user.id, "delete_note", "note", note_id)
    return {"status": "deleted"}
