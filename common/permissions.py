"""
permissions.py - which SCOPES (permissions) each ROLE gets.

A scope is a "resource:action" string, like "tickets:read" or "certificates:issue".
At login the backend copies the user's scopes into the JWT ("scope" claim).
The MCP server then only looks at the scopes in the token - never at this table -
so a token is all it needs to decide what the caller may do.
"""

LEARNER_SCOPES = [
    "faq:read",
    "courses:read",
    "courses:purchase",
    "me:read",
    "tickets:read",
    "tickets:create",
    "tickets:reply",
]

SUPPORT_SCOPES = [
    "faq:read",
    "courses:read",
    "tickets:read",
    "tickets:read_all",
    "tickets:manage",
    "learners:read",
    "access:extend",
    "enrollments:remove",
]

ADMIN_SCOPES = SUPPORT_SCOPES + [
    "access:extend_unlimited",
    "certificates:issue",
    "faq:write",
    "stats:read",
    "users:manage",
]

ROLE_SCOPES = {
    "learner": LEARNER_SCOPES,
    "support": SUPPORT_SCOPES,
    "admin": ADMIN_SCOPES,
}

ALL_SCOPES = list(dict.fromkeys(LEARNER_SCOPES + ADMIN_SCOPES))


def effective_scopes(role: str, custom_scopes: str | None) -> list[str]:
    return custom_scopes.split() if custom_scopes is not None else list(ROLE_SCOPES[role])