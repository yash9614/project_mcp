Startup Steps

1. uv sync
2. jwt secret
python -c "import secrets; print(secrets.token_urlsafe(48))"
3. db
uv run python -m database.db
4. run mcp server
uv run python -m mcp_server.server
5. run backend
uv run python -m backend.app

Extension: SQLite Viewer in order to see the database