# Key Concepts & Interview Q&A — Telusko Support Chat (MCP + JWT + Scopes)

Companion notes for the Telusko Agentic AI Engineering with Python session (11-10-2026).

---

## Most Important Concepts

### 1. Authentication vs Authorization
- **Authentication** = “Who are you?” (Is the JWT valid, unexpired, issued by us, meant for us?)
- **Authorization** = “What may you do?” (Does the token carry the scope this tool requires?)

In this project:
- Authentication is handled by `JWTTokenVerifier` (reject → HTTP 401)
- Authorization is handled by the `check_access` middleware (reject → Access denied result)

### 2. Scopes (`resource:action`)
A scope is a plain string such as `tickets:read`, `certificates:issue`, or `users:manage`.

- Scopes travel **inside the JWT**.
- The MCP server never looks up the user in the database to decide permissions — it only trusts the verified token.
- Tool visibility (`tools/list`) and tool execution (`tools/call`) are both filtered by scopes.

### 3. The Token (JWT)
Key claims:
- `sub` — user id
- `scope` — space-separated list of permissions
- `iss` — issuer (`telusko-auth`)
- `aud` — audience (`telusko-mcp-server`)
- `exp` — expiry

`iss` and `aud` prevent token replay across services. The `require` list rejects tokens that simply omit a claim.

**Important consequence:** When an admin changes a user’s role, the change takes effect only on the next login. The old token remains valid until it expires.

### 4. MCP Middleware (`check_access`)
Runs on every MCP request:
- On `tools/list` → return only the tools the caller has a scope for
- On `tools/call` → refuse the call if the required scope is missing

This is why the sidebar tool list changes when you switch between learner / support / admin.

### 5. Data-level Rules
Some rules cannot be expressed as a simple scope. Example:
- A learner has `tickets:read` but can only open **their own** tickets.
- This is enforced inside the tool (`load_ticket`) after the scope check passes.

### 6. One Client per Request
The backend opens a fresh MCP connection for every chat turn and forwards the user’s JWT. The MCP server therefore always sees the identity of the person currently talking.

### 7. Models Layer Owns All SQL
No tool writes raw SQL. Every database operation goes through the dataclass models in `database/models.py`. This makes the tools file clean and makes a future move to Postgres a small change.

### 8. SQLite by Design
Chosen for the class project because it needs no external server. The schema and models stay the same if you later switch the connection in `database/db.py`.

---

## Interview-Style Questions

**Q: Why put scopes inside the JWT instead of looking up the user on every request?**  
A: So the MCP server can make authorization decisions without a database round-trip and without trusting the backend beyond the shared secret. The token is self-contained and verifiable.

**Q: What happens if an admin changes a user’s role while they are still logged in?**  
A: Nothing until they log in again. The old JWT still carries the old scopes and remains valid until it expires (default 60 minutes).

**Q: How does the system stop a learner from seeing another learner’s ticket?**  
A: Two layers. First, the scope check (`tickets:read` vs `tickets:read_all`). Second, a data-level check inside the tool that compares `ticket.user_id` with the caller’s id.

**Q: Why does the browser never talk to the MCP server directly?**  
A: So the backend can own the conversation, run the tool-calling loop, and keep the MCP server as a pure capability provider. One token, three hops, one identity.

**Q: What is the purpose of `iss` and `aud` in the JWT?**  
A: `iss` says who minted the token. `aud` says who it was minted for. Together they stop a token issued for another service from being accepted here.

**Q: How is tool visibility controlled?**  
A: The `check_access` middleware filters the result of `tools/list`. A tool only appears if the caller’s scopes include the scope required by that tool.

**Q: Why is the frontend a single HTML file?**  
A: So the focus stays on the MCP + auth design. The UI is deliberately simple; the interesting logic lives in the backend and MCP server.

**Q: What would you change to move this project to Postgres?**  
A: Only `database/db.py` (the connection). The schema, seed data, and all model methods stay the same.

**Q: Why does support not get the `courses:purchase` or `me:read` scopes?**  
A: Those scopes are about owning and buying courses. A support agent is not buying anything through this desk.

**Q: How are custom permissions implemented?**  
A: The `users.scopes` column stores a space-separated list. `NULL` means “use the role defaults”. An admin can override this per user from the Manage Users panel.

---

## Quick Mental Model

```
Browser  --JWT-->  Backend  --same JWT-->  MCP Server
                                      └─ verifies token
                                      └─ filters tools by scopes
                                      └─ enforces data-level rules
                                      └─ runs the tool
```

The permission system lives entirely on the server side. The UI and the prompt only reflect what the server already decided.
