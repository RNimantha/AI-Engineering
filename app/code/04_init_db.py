"""
One-command database initialisation script.

Run this once after creating the MySQL database:

    # 1. Create the database (one-time)
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS claude_agent_sdk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

    # 2. Set your credentials (or edit .env)
    export DATABASE_URL="mysql+pymysql://root:your_password@localhost:3306/claude_agent_sdk"

    # 3. Run this script from the project root
    cd /path/to/ClaudeSDK
    python app/code/04_init_db.py

The script is idempotent — running it again does nothing if tables exist.
"""

import os
import sys

# ── Ensure imports resolve relative to the app/ directory ────────────────────
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", )
sys.path.insert(0, os.path.normpath(APP_DIR))

# Load .env so DATABASE_URL is available before importing SQLAlchemy engine
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_DIR, "..", ".env"))
except ImportError:
    pass  # python-dotenv not installed; rely on environment variables

from database import engine, init_db  # noqa: E402 — must come after sys.path tweak
from models import (  # noqa: F401 — side-effect: registers tables with Base.metadata
    AuditLog,
    Conversation,
    InventoryItem,
    Message,
    ToolCall,
    User,
    UserNote,
)


# ── Seed data ─────────────────────────────────────────────────────────────────

SEED_INVENTORY = [
    {"sku": "BATS-001",  "name": "bats",  "quantity": 10},
    {"sku": "BALLS-001", "name": "balls", "quantity": 6},
    {"sku": "CAPS-001",  "name": "caps",  "quantity": 5},
]


def seed_inventory(db) -> None:
    """Seed the three rows from the original inventry.csv if the table is empty."""
    from models import InventoryItem
    if db.query(InventoryItem).count() > 0:
        print("  inventory_items: already has data, skipping seed.")
        return
    for row in SEED_INVENTORY:
        db.add(InventoryItem(**row))
    db.commit()
    print(f"  inventory_items: seeded {len(SEED_INVENTORY)} rows from original CSV.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    sep = "=" * 68
    print(f"\n{sep}")
    print("  Claude Agent SDK — MySQL Database Initialisation")
    print(f"{sep}\n")

    db_url = os.getenv("DATABASE_URL", "(default: root@localhost/claude_agent_sdk)")
    print(f"  Target: {db_url}\n")

    try:
        print("  Creating tables (IF NOT EXISTS) ...")
        init_db()

        from database import SessionLocal
        with SessionLocal() as db:
            seed_inventory(db)

        print("\n  Tables created:")
        table_names = [
            "users           — user accounts and sessions",
            "conversations   — chat threads per user",
            "messages        — individual turns",
            "tool_calls      — agent tool invocations",
            "inventory_items — product inventory (seeded from CSV)",
            "user_notes      — persistent notes",
            "audit_logs      — action trail",
        ]
        for name in table_names:
            print(f"    ✓  {name}")

        print(f"\n{sep}")
        print("  Initialisation complete!")
        print(f"{sep}\n")
        print("  Next steps:")
        print("    1. Copy app/code/01_database.py  →  app/database.py")
        print("    2. Copy app/code/02_models.py    →  app/models.py")
        print("    3. Replace app/controller/controller.py with app/code/03_controller_updated.py")
        print("    4. Update app/main.py (see app/code/07_main_example.py)")
        print("    5. python app/main.py\n")
        return 0

    except Exception as exc:
        print(f"\n  ERROR: {exc}\n")
        import traceback
        traceback.print_exc()
        print("\n  Troubleshooting:")
        print("    • Is MySQL running?  mysql.server start")
        print("    • Does the database exist?  mysql -u root -p -e 'SHOW DATABASES'")
        print("    • Is DATABASE_URL correct in .env?")
        return 1


if __name__ == "__main__":
    sys.exit(main())
