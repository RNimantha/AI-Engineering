
import uvicorn
from dotenv import load_dotenv
load_dotenv() 
from database.database import check_connection, init_db  # noqa: E402

# Initialise tables once at startup (idempotent — safe to call every run)
init_db()

if not check_connection():
    raise RuntimeError(
        "Cannot reach MySQL.  Check DATABASE_URL in .env and that MySQL is running."
    )

# The controller module defines the FastAPI `app` — import it after DB is ready
from controller.controller import app  # noqa: E402


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
