import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_token, decode_token, hash_password, token_digest, verify_password
from app.db.session import get_db
from app.models.entities import User, UserSession
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.services.auth_rate_limit import check_login_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])
s = get_settings()


def _set_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie("access_token", access_token, httponly=True, secure=s.cookie_secure, samesite="strict", max_age=s.access_token_minutes * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=s.cookie_secure, samesite="strict", max_age=s.refresh_token_days * 86400, path="/api/v1/auth")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    if not await check_login_rate_limit(body.email):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = UserSession(user_id=user.id, refresh_jti=uuid.uuid4().hex, refresh_token_hash="", expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_days))
    db.add(session)
    await db.flush()

    access_token = create_token(str(user.id), "access", timedelta(minutes=s.access_token_minutes), session_id=str(session.id))
    refresh_token = create_token(str(user.id), "refresh", timedelta(days=s.refresh_token_days), session_id=str(session.id), jti=session.refresh_jti)
    session.refresh_token_hash = token_digest(refresh_token)
    await db.commit()

    _set_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        decoded = decode_token(body.refresh_token, "refresh")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    session = await db.scalar(select(UserSession).where(UserSession.id == uuid.UUID(decoded.session_id)))
    if not session or session.revoked_at:
        if session:
            # Possible token reuse — revoke all sessions for this user
            all_sessions = await db.execute(select(UserSession).where(UserSession.user_id == session.user_id))
            for s in all_sessions.scalars():
                s.revoked_at = datetime.now(timezone.utc)
            await db.commit()
        raise HTTPException(status_code=401, detail="Session invalid")

    # Rotate: revoke old, create new
    session.revoked_at = datetime.now(timezone.utc)
    new_session = UserSession(
        user_id=session.user_id, refresh_jti=uuid.uuid4().hex, refresh_token_hash="",
        expires_at=datetime.now(timezone.utc) + timedelta(days=s.refresh_token_days),
        rotated_from_session_id=session.id,
    )
    db.add(new_session)
    await db.flush()

    access_token = create_token(str(session.user_id), "access", timedelta(minutes=s.access_token_minutes), session_id=str(new_session.id))
    refresh_token = create_token(str(session.user_id), "refresh", timedelta(days=s.refresh_token_days), session_id=str(new_session.id), jti=new_session.refresh_jti)
    new_session.refresh_token_hash = token_digest(refresh_token)
    await db.commit()

    _set_cookies(response, access_token, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout(response: Response, db: AsyncSession = Depends(get_db)):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return {"status": "ok"}