from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_token,
    decode_token,
    needs_password_rehash,
    token_digest,
    verify_password,
    hash_password,
)
from app.db.session import get_db
from app.models.entities import User, UserSession
from app.schemas.auth import LoginRequest, TokenPair, SessionResponse
from app.services.auth_rate_limit import check_login_budget

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")


def _context_hash(value: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


async def _issue_session(
    db: AsyncSession,
    user: User,
    request: Request,
    *,
    rotated_from_session_id: uuid.UUID | None = None,
) -> TokenPair:
    s = get_settings()
    session_id = uuid.uuid4()
    refresh_jti = uuid.uuid4().hex
    refresh = create_token(
        str(user.id),
        "refresh",
        timedelta(days=s.refresh_token_days),
        session_id=str(session_id),
        jti=refresh_jti,
    )
    access = create_token(
        str(user.id),
        "access",
        timedelta(minutes=s.access_token_minutes),
        session_id=str(session_id),
    )
    now = datetime.now(timezone.utc)
    db.add(UserSession(
        id=session_id,
        user_id=user.id,
        refresh_jti=refresh_jti,
        refresh_token_hash=token_digest(refresh),
        expires_at=now + timedelta(days=s.refresh_token_days),
        rotated_from_session_id=rotated_from_session_id,
        user_agent_hash=_context_hash(request.headers.get("user-agent", "")) if request.headers.get("user-agent") else None,
        ip_hash=_context_hash(_client_ip(request)),
    ))
    return TokenPair(access_token=access, refresh_token=refresh)


def _set_session_cookies(response: Response, pair: TokenPair) -> None:
    s = get_settings()
    response.set_cookie(
        "access_token",
        pair.access_token,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        max_age=s.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        pair.refresh_token,
        httponly=True,
        secure=s.cookie_secure,
        samesite="strict",
        max_age=s.refresh_token_days * 86400,
        path=f"{s.api_v1_prefix}/auth",
    )


async def _authenticate(payload: LoginRequest, request: Request, db: AsyncSession) -> User:
    allowed, retry_after = await check_login_budget(payload.email, _client_ip(request))
    if not allowed:
        raise HTTPException(status_code=429, detail="too many login attempts", headers={"Retry-After": str(retry_after)})
    user = await db.scalar(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if needs_password_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    return user


@router.post("/login", response_model=SessionResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await _authenticate(payload, request, db)
    pair = await _issue_session(db, user, request)
    await db.commit()
    _set_session_cookies(response, pair)
    return SessionResponse(ok=True, user_id=str(user.id), role=user.role)


@router.post("/token", response_model=TokenPair)
async def token(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await _authenticate(payload, request, db)
    pair = await _issue_session(db, user, request)
    await db.commit()
    return pair


@router.post("/refresh", response_model=SessionResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(status_code=401, detail="refresh token required")
    try:
        decoded = decode_token(raw, "refresh")
        session_id = uuid.UUID(decoded.session_id)
        user_id = uuid.UUID(decoded.subject)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="invalid refresh token")

    session = await db.scalar(select(UserSession).where(UserSession.id == session_id).with_for_update())
    now = datetime.now(timezone.utc)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=401, detail="invalid session")

    if session.revoked_at is not None:
        await db.execute(update(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        ).values(revoked_at=now))
        await db.commit()
        raise HTTPException(status_code=401, detail="refresh token reuse detected; sessions revoked")

    if session.expires_at <= now or session.refresh_jti != decoded.jti or not hmac.compare_digest(session.refresh_token_hash, token_digest(raw)):
        session.revoked_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="invalid refresh session")

    user = await db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        session.revoked_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="inactive user")

    session.revoked_at = now
    session.last_used_at = now
    pair = await _issue_session(db, user, request, rotated_from_session_id=session.id)
    await db.commit()
    _set_session_cookies(response, pair)
    return SessionResponse(ok=True, user_id=str(user.id), role=user.role)


@router.post("/logout", response_model=SessionResponse)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get("refresh_token")
    if raw:
        try:
            decoded = decode_token(raw, "refresh")
            session = await db.get(UserSession, uuid.UUID(decoded.session_id))
            if session and session.revoked_at is None:
                session.revoked_at = datetime.now(timezone.utc)
                await db.commit()
        except (ValueError, TypeError):
            pass
    s = get_settings()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=f"{s.api_v1_prefix}/auth")
    return SessionResponse(ok=True)


@router.post("/logout-all", response_model=SessionResponse)
async def logout_all(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw = request.cookies.get("refresh_token") or request.cookies.get("access_token")
    if not raw:
        raise HTTPException(status_code=401, detail="session required")
    expected = "refresh" if request.cookies.get("refresh_token") else "access"
    try:
        decoded = decode_token(raw, expected)
        user_id = uuid.UUID(decoded.subject)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="invalid session")
    await db.execute(update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)).values(
        revoked_at=datetime.now(timezone.utc)
    ))
    await db.commit()
    s = get_settings()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=f"{s.api_v1_prefix}/auth")
    return SessionResponse(ok=True, user_id=str(user_id))
