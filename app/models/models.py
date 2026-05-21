"""
SQLAlchemy ORM models for the Claude Agent SDK demo.

Tables:
    users           — user accounts tied to frontend session IDs
    conversations   — chat threads belonging to a user
    messages        — individual turns within a conversation
    tool_calls      — agent tool invocations logged per assistant message
    inventory_items — product inventory (replaces inventry.csv)
    user_notes      — persistent notes (replaces in-memory store in notes_server.py)
    audit_logs      — optional action trail for debugging

Relationship hierarchy:
    User
    └─ Conversation (many)
       └─ Message (many)
          └─ ToolCall (many)
    User ─ InventoryItem (many, user_id nullable → global items)
    User ─ UserNote (many)

Place this file at: app/models/models.py

IMPORTANT: Column named `extra_data` is used instead of `metadata` because
`metadata` is a reserved attribute on SQLAlchemy's DeclarativeBase class.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.database import Base


# ── Users & sessions ───────────────────────────────────────────────────────────

class User(Base):
    """
    Application users.  Each browser session is mapped to one User row via
    the session_id UUID that the frontend stores in localStorage.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)

    # Frontend-generated UUID (stored in localStorage, sent as X-Session-ID header)
    session_id = Column(String(255), unique=True, index=True, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    # Flexible JSON bag for any extra user attributes; avoids schema changes
    extra_data = Column(JSON, default=dict, nullable=True)

    # Relationships (cascade deletes propagate to child rows)
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    inventory_items = relationship("InventoryItem", back_populates="user")
    notes = relationship(
        "UserNote", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ── Conversations & messages ───────────────────────────────────────────────────

class Conversation(Base):
    """
    A chat thread.  Created on the first message of a new session or when
    the user explicitly starts a fresh chat.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Conversation", nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )
    is_archived = Column(Boolean, default=False, nullable=False)
    extra_data = Column(JSON, default=dict, nullable=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id} title={self.title[:30]!r}>"


class Message(Base):
    """
    One turn in a conversation.  role is 'user' or 'assistant'.
    Each assistant Message may have zero or more associated ToolCall rows.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(50), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    extra_data = Column(JSON, default=dict, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    tool_calls = relationship(
        "ToolCall", back_populates="message", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role!r} conv_id={self.conversation_id}>"


# ── Tool calls ─────────────────────────────────────────────────────────────────

class ToolCall(Base):
    """
    Records each tool invocation that the agent emits during a response turn.

    The agent stream yields AgentEvent(type='tool', content=tool_name) when a
    tool is called.  At that point we create a ToolCall row with status='triggered'.
    Since the Claude Agent SDK does not expose tool input/output at the streaming
    layer we cannot populate tool_input / tool_output here; extend agents.py if
    you need those fields.
    """

    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name = Column(String(100), nullable=False, index=True)
    # JSON input args (populated if available from the agent; otherwise empty dict)
    tool_input = Column(JSON, nullable=False, default=dict)
    # JSON result (populated after tool completes; nullable until then)
    tool_output = Column(JSON, nullable=True)
    # "triggered" → agent called the tool; "success" / "error" → result known
    status = Column(String(50), default="triggered", nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Float, nullable=True)

    message = relationship("Message", back_populates="tool_calls")

    def __repr__(self) -> str:
        return f"<ToolCall id={self.id} tool={self.tool_name!r} status={self.status!r}>"


# ── Inventory ──────────────────────────────────────────────────────────────────

class InventoryItem(Base):
    """
    Product inventory.  Replaces app/csv/inventry.csv.

    user_id=NULL means the item is shared / global.
    The existing tools (get_inventory, get_item, update_stock) can be
    updated to query this table instead of reading the CSV.

    Column `name` matches the CSV's 'name' field.
    Column `quantity` matches the CSV's 'quntity' field (note: typo fixed in DB).
    """

    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sku = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )
    extra_data = Column(JSON, default=dict, nullable=True)

    user = relationship("User", back_populates="inventory_items")

    def __repr__(self) -> str:
        return f"<InventoryItem sku={self.sku!r} name={self.name!r} qty={self.quantity}>"


# ── User notes ─────────────────────────────────────────────────────────────────

class UserNote(Base):
    """
    Persistent notes.  Replaces the in-memory _notes dict in notes_server.py.

    The MCP notes server can be updated to read/write this table instead of
    the dict to survive restarts without any frontend changes.
    """

    __tablename__ = "user_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )
    is_pinned = Column(Boolean, default=False, nullable=False)
    extra_data = Column(JSON, default=dict, nullable=True)

    user = relationship("User", back_populates="notes")

    def __repr__(self) -> str:
        return f"<UserNote id={self.id} user_id={self.user_id} title={self.title[:30]!r}>"


# ── Audit log ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Optional append-only action log for debugging and compliance.

    Written by controller helpers (log_audit).  Not required for basic
    operation; safe to disable by never calling log_audit().
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # no FK so logs survive user deletion
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} user_id={self.user_id}>"
