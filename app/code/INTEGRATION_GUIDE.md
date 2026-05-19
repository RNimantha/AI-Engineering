# MySQL Integration Guide — Claude Agent SDK Demo

## What changes

| Data | Before | After |
|------|--------|-------|
| Conversations | Lost on restart | MySQL `conversations` + `messages` |
| Tool calls | Logs only | MySQL `tool_calls` (name + timing) |
| Inventory | `app/csv/inventry.csv` | MySQL `inventory_items` |
| Notes | In-memory dict (lost) | MySQL `user_notes` |
| User sessions | None | MySQL `users` (keyed by `X-Session-ID` header) |

**Zero changes** to `app/agent/agents.py`, the Claude SDK integration, or the React frontend.

---

## Prerequisites

- MySQL 8.x (or 5.7+)
- Python 3.11+
- `uv` or `pip`

---

## Step 1 — Install packages

```bash
# From project root
pip install sqlalchemy pymysql python-dotenv
# or
uv pip install sqlalchemy pymysql python-dotenv
```

---

## Step 2 — Set up environment

```bash
cp app/code/06_env_template .env
```

Edit `.env`:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/claude_agent_sdk
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Step 3 — Create the database

```bash
mysql -u root -p -e \
  "CREATE DATABASE IF NOT EXISTS claude_agent_sdk \
   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## Step 4 — Copy files into the project

```bash
# From project root
cp app/code/01_database.py           app/database.py
cp app/code/02_models.py             app/models.py
cp app/code/03_controller_updated.py app/controller/controller.py
```

> The updated controller is a **drop-in replacement** — it defines the same
> `app` FastAPI instance with `/api/health` and `/api/chat` unchanged, plus
> new endpoints for conversations, inventory, and notes.

---

## Step 5 — Initialise tables

```bash
python app/code/04_init_db.py
```

Expected output:

```
====================================================================
  Claude Agent SDK — MySQL Database Initialisation
====================================================================

  Creating tables (IF NOT EXISTS) ...
  inventory_items: seeded 3 rows from original CSV.

  Tables created:
    ✓  users           — user accounts and sessions
    ✓  conversations   — chat threads per user
    ✓  messages        — individual turns
    ✓  tool_calls      — agent tool invocations
    ✓  inventory_items — product inventory (seeded from CSV)
    ✓  user_notes      — persistent notes
    ✓  audit_logs      — action trail
```

Verify:

```bash
mysql -u root -p claude_agent_sdk -e "SHOW TABLES;"
```

---

## Step 6 — Update app/main.py

Replace `app/main.py` with the contents of `app/code/07_main_example.py`, **or** apply these two minimal additions to the existing file:

```python
# 1. At the top, after existing imports
from dotenv import load_dotenv
load_dotenv()  # must be before database import

# 2. Replace the existing @app.on_event("startup") / lifespan, or add:
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    from database import init_db
    init_db()
    yield

# Pass lifespan= to FastAPI():
app = FastAPI(title="ClaudeSDK Chat API", lifespan=lifespan)
```

---

## Step 7 — Start and test

```bash
# Terminal 1 — backend
cd /path/to/ClaudeSDK/app
python main.py

# Terminal 2 — notes MCP server (unchanged)
python mcp_servers/notes_server.py

# Terminal 3 — frontend (unchanged)
cd /path/to/ClaudeSDK/frontend
npm run dev
```

Open http://localhost:5173, send a message, restart the backend, reload the
page — the conversation history is gone from the UI (the frontend holds
history in React state) but the data is in MySQL and accessible via the
`/api/conversations` endpoint.

---

## Step 8 — Optional: persistent history in the frontend

The frontend currently holds all chat history in React state.  To show
history across page loads, add a session ID header to every request:

```typescript
// frontend/src/utils/session.ts
export const SESSION_ID =
  localStorage.getItem("sessionId") ?? crypto.randomUUID();
localStorage.setItem("sessionId", SESSION_ID);
```

```typescript
// frontend/src/useChat.ts  — inside sendMessage(), add to headers:
"X-Session-ID": SESSION_ID,
```

Then on mount call `GET /api/conversations` (with the header) to load
history and `GET /api/conversations/{id}` to restore a thread.

---

## Verify data in MySQL

```sql
USE claude_agent_sdk;

-- Users created per session
SELECT id, username, session_id, last_active FROM users;

-- Conversations
SELECT id, user_id, title, created_at FROM conversations ORDER BY id DESC LIMIT 10;

-- Recent messages
SELECT m.id, m.role, LEFT(m.content, 60) AS content, m.created_at
FROM messages m ORDER BY m.created_at DESC LIMIT 20;

-- Tool calls
SELECT tc.id, tc.tool_name, tc.status, tc.created_at
FROM tool_calls tc ORDER BY tc.created_at DESC LIMIT 20;

-- Inventory (seeded from CSV)
SELECT * FROM inventory_items;
```

---

## Troubleshooting

### "Can't connect to MySQL server"
```bash
mysql.server start        # macOS
sudo service mysql start  # Linux
mysql -u root -p -e "SELECT 1"  # verify
```

### "Access denied for user 'root'"
Check `DATABASE_URL` in `.env`; confirm password with `mysql -u root -p`.

### "No module named 'sqlalchemy'"
```bash
pip install sqlalchemy pymysql
```

### "Table already exists"
Safe to ignore — `init_db()` uses `CREATE TABLE IF NOT EXISTS`.

### ImportError on `from database import ...`
Make sure you're running from `app/` as the working directory, or that
`app/` is on `sys.path`.  The `04_init_db.py` script handles this automatically.

### CORS error in browser
Verify `CORS_ORIGINS` in `.env` matches the Vite dev server URL
(`http://localhost:5173` by default).

---

## Architecture notes

### Why `extra_data` not `metadata`?
SQLAlchemy's `DeclarativeBase` reserves the name `metadata` as a class-level
attribute (it holds the `MetaData` object used for `create_all`).  Using a
column named `metadata` shadows that attribute and breaks SQLAlchemy
internals.  All JSON columns are named `extra_data` instead.

### Why a second db session inside `event_generator`?
FastAPI's `Depends(get_db)` session is valid for the duration of the request.
For SSE responses the request is held open until the stream ends, so the
session technically stays alive.  However, SQLAlchemy sessions are not
thread-safe and the async generator runs in a different coroutine context.
Creating a dedicated `SessionLocal()` inside the generator keeps the session
lifecycle explicit and avoids subtle race conditions.

### Tool call tracking
The Claude Agent SDK stream yields `AgentEvent(type="tool", content=tool_name)`
when a tool is invoked.  At the streaming layer, tool input/output is not
exposed.  Each such event creates a `ToolCall` row with `status="triggered"`.
To populate `tool_input` and `tool_output`, instrument individual tool
functions in `app/tools/` to write to the DB directly.

### Conversation continuity
The backend uses a heuristic to continue the current conversation:
if the stored message count equals `len(incoming_messages) - 1`, the new
request is the next turn of the same thread.  Otherwise a new conversation
is created.  This works because the frontend sends the full history on each
request.  Once the frontend sends an `X-Session-ID` header the matching
is tied to a specific user, preventing cross-session collisions.

---

## Success checklist

- [ ] MySQL running, `claude_agent_sdk` database created
- [ ] `.env` file present with correct `DATABASE_URL`
- [ ] `python app/code/04_init_db.py` completes without error
- [ ] `SHOW TABLES` returns 7 tables
- [ ] `app/database.py`, `app/models.py` copied
- [ ] `app/controller/controller.py` replaced with updated version
- [ ] `app/main.py` calls `init_db()` on startup
- [ ] Backend starts without import errors
- [ ] Chat message appears in `SELECT * FROM messages` after sending
- [ ] Backend restart does not lose inventory data (query `inventory_items`)
