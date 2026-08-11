from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.webhook_security import verify_meta_signature, verify_telegram_secret, verify_rubika_signature
from app.services.inbound import process_inbound_message

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp")
async def verify_whatsapp_webhook(hub_mode: str, hub_challenge: str, hub_verify_token: str):
    from app.core.config import get_settings
    s = get_settings()
    if hub_mode == "subscribe" and hub_verify_token == s.webhook_verify_token:
        return int(hub_challenge)
    return {"status": "denied"}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_meta_signature(signature, body):
        return {"status": "invalid_signature"}
    data = await request.json()
    entries = data.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            messages = change.get("value", {}).get("messages", [])
            for msg in messages:
                await process_inbound_message(db, channel="WHATSAPP", sender_id=msg.get("from", ""), text=msg.get("text", {}).get("body", ""), external_message_id=msg.get("id"))
    await db.commit()
    return {"status": "ok"}


@router.post("/telegram")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not verify_telegram_secret(secret):
        return {"status": "invalid_secret"}
    data = await request.json()
    msg = data.get("message", {})
    if msg:
        await process_inbound_message(db, channel="TELEGRAM", sender_id=str(msg.get("chat", {}).get("id", "")), text=msg.get("text", ""), external_message_id=str(msg.get("message_id", "")))
    await db.commit()
    return {"status": "ok"}


@router.post("/eitaa")
async def eitaa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    msg = data.get("message", {})
    if msg:
        await process_inbound_message(db, channel="EITAA", sender_id=str(msg.get("chat", {}).get("id", "")), text=msg.get("text", ""), external_message_id=str(msg.get("message_id", "")))
    await db.commit()
    return {"status": "ok"}


@router.post("/rubika")
async def rubika_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Rubika-Signature", "")
    if not verify_rubika_signature(signature, body):
        return {"status": "invalid_signature"}
    data = await request.json()
    msg = data.get("message", {})
    if msg:
        await process_inbound_message(db, channel="RUBIKA", sender_id=str(msg.get("chat", {}).get("id", "")), text=msg.get("text", ""), external_message_id=str(msg.get("message_id", "")))
    await db.commit()
    return {"status": "ok"}