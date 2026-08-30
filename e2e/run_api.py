import asyncio
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = ROOT / "apps" / "api"

sys.path.insert(0, str(API))
os.chdir(API)

db = API / "e2e.db"
if db.exists():
    db.unlink()

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./e2e.db"
os.environ["STORAGE_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LLM_PROVIDER"] = "none"
os.environ["EXTRACTION_INLINE"] = "true"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

from app.seed import seed  # noqa: E402

asyncio.run(seed())

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="warning")