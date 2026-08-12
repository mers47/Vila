from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.redis_pool import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    # Liveness must not depend on external services; otherwise an outage causes a restart storm.
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    try:
        async with asyncio.timeout(3):
            async with SessionLocal() as db:
                await db.execute(text("SELECT 1"))
            await redis_client().ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="dependencies not ready") from exc
    return {"status": "ready"}
