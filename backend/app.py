"""
backend/app.py - FastAPI chat backend (port 8000).
Run from the project root:  python -m backend.app

Flow for every chat message:
    Browser --(JWT)--> /api/chat
        -> connect to MCP server with the SAME JWT as a Bearer token
        -> tools/list   (the MCP server only returns tools allowed for this role)
        -> LLM decides which tool(s) to call  -> tools/call on the MCP server
        -> loop until the LLM gives a final answer
    <-- reply + a trace of the tool calls (shown in the UI for teaching)

The browser NEVER talks to the MCP server directly.
"""

import json
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel

from common.auth import create_token, decode_token
from common.config import LLM_MODEL, MCP_SERVER_URL, PROJECT_ROOT
from common.prompts import build_system_prompt
from database.models import User

app = FastAPI(title="Telusko Support Chat")
llm = ChatOpenAI(model=LLM_MODEL)  # API key comes from OPENAI_API_KEY in .env

MAX_TOOL_ROUNDS = 8


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/login")
def login(body: LoginRequest):
    user = User.get_by_email(body.email)
    if user is None or not user.check_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user.to_dict()), "user": user.to_dict()}


def get_current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"token": token, "id": int(claims["sub"]), "name": claims["name"],
            "email": claims["email"], "role": claims["role"], "scopes": claims["scope"].split()}


@asynccontextmanager
async def mcp_client(token: str):
    """Connect to the MCP server, forwarding the user's JWT as a Bearer token."""
    http = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=60)
    async with http, Client(streamable_http_client(MCP_SERVER_URL, http_client=http)) as client:
        yield client


def result_text(result) -> str:
    return "\n".join(c.text for c in result.content if getattr(c, "text", None)) or "(no output)"


def mcp_tools_to_langchain(tools) -> list[dict]:
    return [{"name": t.name, "description": t.description or "", "parameters": t.input_schema} for t in tools]


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.post("/api/chat")
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    messages = [SystemMessage(build_system_prompt(user))]
    for m in body.messages:
        if m.role == "user":
            messages.append(HumanMessage(m.content))
        elif m.role == "assistant":
            messages.append(AIMessage(m.content))

    trace = []

    async with mcp_client(user["token"]) as mcp:
        llm_with_tools = llm.bind_tools(mcp_tools_to_langchain((await mcp.list_tools()).tools))

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response: AIMessage = await llm_with_tools.ainvoke(messages)
            except Exception as e:
                return {"reply": f"LLM error: {e}", "tool_calls": trace}

            if not response.tool_calls:
                return {"reply": response.text or "", "tool_calls": trace}

            messages.append(response)

            for tc in response.tool_calls:
                result = await mcp.call_tool(tc["name"], tc["args"])
                text = result_text(result)
                trace.append({"name": tc["name"], "arguments": tc["args"],
                              "is_error": bool(result.is_error), "result": text})
                messages.append(ToolMessage(content=text, tool_call_id=tc["id"]))

    return {"reply": "Sorry, I couldn't finish that request (too many tool calls).", "tool_calls": trace}


@app.get("/api/me")
async def me(user: dict = Depends(get_current_user)):
    async with mcp_client(user["token"]) as mcp:
        tools = (await mcp.list_tools()).tools
    return {"user": {k: user[k] for k in ("id", "name", "email", "role")}, "scopes": user["scopes"],
            "tools": [{"name": t.name, "description": t.description} for t in tools]}


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    scopes: list[str] | None = None


class UpdateUserRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    role: str | None = None
    password: str | None = None
    scopes: list[str] | None = None
    use_role_defaults: bool = False


async def call_tool_json(token: str, name: str, arguments: dict) -> dict:
    async with mcp_client(token) as mcp:
        result = await mcp.call_tool(name, arguments)
    if result.is_error:
        detail = result_text(result)
        if detail.startswith("Error executing tool"):
            detail = detail.split(": ", 1)[-1]
        raise HTTPException(status_code=403 if detail.startswith("Access denied") else 400, detail=detail)
    return json.loads(result_text(result))


@app.get("/api/users")
async def list_users(user: dict = Depends(get_current_user)):
    return await call_tool_json(user["token"], "list_users", {})


@app.post("/api/users")
async def create_user(body: CreateUserRequest, user: dict = Depends(get_current_user)):
    return await call_tool_json(user["token"], "create_user", body.model_dump(exclude_none=True))


@app.put("/api/users/{user_id}")
async def update_user(user_id: int, body: UpdateUserRequest, user: dict = Depends(get_current_user)):
    arguments = {"user_id": user_id, **body.model_dump(exclude_none=True)}
    if not arguments.get("password"):
        arguments.pop("password", None)
    return await call_tool_json(user["token"], "update_user", arguments)


@app.get("/api/courses")
async def list_courses(user: dict = Depends(get_current_user)):
    courses = (await call_tool_json(user["token"], "list_courses", {}))["courses"]
    enrollments = []
    if "me:read" in user["scopes"]:
        enrollments = (await call_tool_json(user["token"], "get_my_enrollments", {}))["enrollments"]
    active = {e["course_id"]: e["access_valid_till"] for e in enrollments if not e["access_expired"]}
    return {"courses": [{**c, "access_valid_till": active.get(c["id"])} for c in courses]}


class PurchaseRequest(BaseModel):
    course_title: str


@app.post("/api/courses/{course_id}/purchase")
async def purchase_course(course_id: int, body: PurchaseRequest, user: dict = Depends(get_current_user)):
    return await call_tool_json(user["token"], "purchase_course",
                                {"course_id": course_id, "course_title": body.course_title})


@app.get("/")
def index():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)