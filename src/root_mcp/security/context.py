"""Request context carried through policy and authorization checks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    """Identity and deployment facts associated with one MCP request."""

    deployment_profile: Literal["local", "central"]
    transport: Literal["stdio", "streamable_http"]
    principal_id: str | None = None
    tenant_id: str | None = None
    session_id: str | None = None
    roles: set[str] = Field(default_factory=set)
    resource_scopes: set[str] = Field(default_factory=set)
    request_id: str
