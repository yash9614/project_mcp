"""
Shared configuration for the Telusko Support Chat demo.

Values come from the .env file (see .env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- Database ---------------------------------------------------------------
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "database" / "telusko.db"))

# --- JWT (shared secret between backend and MCP server) ---------------------
JWT_SECRET = os.getenv("JWT_SECRET", "")
if len(JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET is missing or shorter than 32 characters. Set it in the .env file in the project root.\n"
        'Generate one with:  python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "telusko-auth"
JWT_AUDIENCE = "telusko-mcp-server"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))

# --- Servers ----------------------------------------------------------------
BACKEND_PORT = 8000
MCP_PORT = 8001
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")

# --- LLM (OpenAI via LangChain) -----------------------------------------------
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")