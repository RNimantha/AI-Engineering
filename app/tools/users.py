import csv
import uuid
from pathlib import Path

from claude_agent_sdk import tool

CSV_PATH = Path(__file__).parent.parent / "csv" / "users_details.csv"
FIELDS = ["id", "frist_name", "last_name", "email", "phone", "dob", "address", "age"]


def _read_rows() -> list[dict]:
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))


def _write_rows(rows: list[dict]) -> None:
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _find_user(rows: list[dict], query: str) -> dict | None:
    q = query.strip().lower()
    for row in rows:
        if (
            row["id"] == q
            or row["email"].lower() == q
            or f"{row['frist_name']} {row['last_name']}".lower() == q
        ):
            return row
    return None


def _format_user(row: dict) -> str:
    return (
        f"id={row['id']} name={row['frist_name']} {row['last_name']} "
        f"email={row['email']} phone={row['phone']} dob={row['dob']} "
        f"address={row['address']} age={row['age']}"
    )


@tool("get_all_users", "List all users from the users details CSV", {})
async def get_all_users(args):
    rows = _read_rows()
    lines = [_format_user(r) for r in rows]
    return {"content": [{"type": "text", "text": "\n".join(lines) or "No users found"}]}


@tool(
    "get_user",
    "Get a single user by id, email, or full name",
    {"query": str},
)
async def get_user(args):
    rows = _read_rows()
    row = _find_user(rows, args["query"])
    if row:
        return {"content": [{"type": "text", "text": _format_user(row)}]}
    return {
        "content": [{"type": "text", "text": f"User '{args['query']}' not found"}],
        "is_error": True,
    }


@tool(
    "create_user",
    "Create a new user. Provide first_name, last_name, email, phone, dob (YYYY-MM-DD), address, age.",
    {
        "first_name": str,
        "last_name": str,
        "email": str,
        "phone": str,
        "dob": str,
        "address": str,
        "age": int,
    },
)
async def create_user(args):
    rows = _read_rows()
    # Prevent duplicate email
    for row in rows:
        if row["email"].lower() == args["email"].strip().lower():
            return {
                "content": [{"type": "text", "text": f"User with email '{args['email']}' already exists"}],
                "is_error": True,
            }
    new_id = str(max((int(r["id"]) for r in rows), default=0) + 1)
    new_row = {
        "id": new_id,
        "frist_name": args["first_name"].strip(),
        "last_name": args["last_name"].strip(),
        "email": args["email"].strip(),
        "phone": args["phone"].strip(),
        "dob": args["dob"].strip(),
        "address": args["address"].strip(),
        "age": str(args["age"]),
    }
    rows.append(new_row)
    _write_rows(rows)
    return {"content": [{"type": "text", "text": f"Created user: {_format_user(new_row)}"}]}


@tool(
    "update_user",
    "Update one or more fields for a user. Identify by id, email, or full name. Provide only fields to change.",
    {
        "query": str,
        "first_name": str,
        "last_name": str,
        "email": str,
        "phone": str,
        "dob": str,
        "address": str,
        "age": int,
    },
)
async def update_user(args):
    rows = _read_rows()
    row = _find_user(rows, args["query"])
    if not row:
        return {
            "content": [{"type": "text", "text": f"User '{args['query']}' not found"}],
            "is_error": True,
        }
    field_map = {
        "first_name": "frist_name",
        "last_name": "last_name",
        "email": "email",
        "phone": "phone",
        "dob": "dob",
        "address": "address",
        "age": "age",
    }
    updated = []
    for arg_key, csv_key in field_map.items():
        val = args.get(arg_key)
        if val is not None and str(val).strip():
            row[csv_key] = str(val).strip()
            updated.append(arg_key)
    _write_rows(rows)
    return {
        "content": [
            {"type": "text", "text": f"Updated fields {updated} → {_format_user(row)}"}
        ]
    }


@tool(
    "delete_user",
    "Delete a user by id, email, or full name",
    {"query": str},
)
async def delete_user(args):
    rows = _read_rows()
    row = _find_user(rows, args["query"])
    if not row:
        return {
            "content": [{"type": "text", "text": f"User '{args['query']}' not found"}],
            "is_error": True,
        }
    rows.remove(row)
    _write_rows(rows)
    return {
        "content": [
            {"type": "text", "text": f"Deleted user: {_format_user(row)}"}
        ]
    }
