"""Explicitly enabled administrative onboarding of public Telegram groups."""

import asyncio
import hmac
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from pyrogram.errors import FloodWait, RPCError

from backend.services.session_clients import SessionBusyError


bearer = HTTPBearer(auto_error=False)


def require_chat_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    token = os.getenv("PARSER_CHAT_ADMIN_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(503, "Chat onboarding is disabled")
    if credentials is None or not hmac.compare_digest(
        credentials.credentials.encode(), token.encode()
    ):
        raise HTTPException(401, "Invalid administrator token", headers={"WWW-Authenticate": "Bearer"})


router = APIRouter(dependencies=[Depends(require_chat_admin)])


class JoinChatRequest(BaseModel):
    account_id: int = Field(gt=0)
    username: str = Field(min_length=5, max_length=32)

    @field_validator("username")
    @classmethod
    def public_username(cls, value):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", value):
            raise ValueError("Use a public group username, without @ or a URL")
        return value.lower()


def realtime(request: Request):
    service = getattr(request.app.state, "realtime_service", None)
    if service is None:
        raise HTTPException(503, "Realtime service is unavailable")
    return service


@router.get("/status")
async def status(request: Request):
    return realtime(request).onboarding_status()


@router.post("/join")
async def join_chat(body: JoinChatRequest, request: Request):
    allowed = {name.strip().lower() for name in os.getenv("PARSER_JOIN_ALLOWED_USERNAMES", "").split(",") if name.strip()}
    if body.username not in allowed:
        raise HTTPException(403, "Group is not in the onboarding allowlist")
    try:
        return await asyncio.wait_for(
            realtime(request).join_selected_chat(body.account_id, body.username), timeout=60
        )
    except SessionBusyError:
        raise HTTPException(409, "Realtime session is busy or disconnected; retry later")
    except FloodWait as exc:
        raise HTTPException(429, "Telegram rate limit; do not switch accounts to retry", headers={"Retry-After": str(max(1, exc.value))})
    except asyncio.TimeoutError:
        raise HTTPException(504, "Operation timed out; retry the same account and group to reconcile membership")
    except PermissionError:
        raise HTTPException(409, "Telegram membership could not be confirmed")
    except ValueError:
        raise HTTPException(400, "Unknown account or target is not a public group")
    except RPCError as exc:
        # Error classes are useful for diagnosis; Telegram payloads may contain secrets.
        raise HTTPException(502, f"Telegram rejected the operation: {type(exc).__name__}")
    except Exception:
        raise HTTPException(500, "Onboarding failed; retry the same account and group to reconcile state")
