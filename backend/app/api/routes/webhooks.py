from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.webhook_security import verify_meta_signature
from app.db.session import get_db
from app.services.inbound import record_inbound
from app.services.message_status import update_external_status

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/meta")
async def verify_meta(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
):
    s = get_settings()
    if hub_mode == "subscribe" and s.webhook_verify_token and hub_verify_token == s.webhook_verify_token:
        return int(hub_challenge or "0")
    raise HTTPException(status_code=403, detail="verification failed")


@router.post("/meta")
async def meta_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    raw = await request.body()
    s = get_settings()
    if not verify_meta_signature(raw, x_hub_signature_256, s.meta_app_secret):
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    payload = await request.json()
    processed = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []) or []:
                sender = msg.get("from")
                text = (msg.get("text") or {}).get("body")
                if sender and text:
                    processed.append(await record_inbound(
                        db, channel="WHATSAPP", sender=sender, body=text,
                        external_message_id=msg.get("id"),
                    ))
            for status_item in value.get("statuses", []) or []:
                ext_id = status_item.get("id")
                state = status_item.get("status")
                errors = status_item.get("errors") or []
                detail = str(errors[0]) if errors else None
                if ext_id and state:
                    await update_external_status(db, ext_id, state, detail)

        for messaging in entry.get("messaging", []) or []:
            sender = (messaging.get("sender") or {}).get("id")
            msg = messaging.get("message") or {}
            text = msg.get("text")
            if sender and text and not msg.get("is_echo"):
                processed.append(await record_inbound(
                    db, channel="INSTAGRAM", sender=sender, body=text,
                    external_message_id=msg.get("mid"),
                ))
            delivery = messaging.get("delivery") or {}
            for mid in delivery.get("mids", []) or []:
                await update_external_status(db, mid, "delivered")
            read = messaging.get("read") or {}
            if read.get("mid"):
                await update_external_status(db, read["mid"], "read")
    return {"ok": True, "processed": processed}


@router.post("/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    secret = get_settings().telegram_webhook_secret
    if not secret or x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="invalid telegram webhook secret")
    payload = await request.json()
    msg = payload.get("message") or payload.get("edited_message") or {}
    chat = msg.get("chat") or {}
    sender_obj = msg.get("from") or {}
    text = msg.get("text") or msg.get("caption")
    if not chat.get("id") or not text:
        return {"ok": True, "processed": False}
    display = " ".join(filter(None, [sender_obj.get("first_name"), sender_obj.get("last_name")])).strip()
    if sender_obj.get("username"):
        display = f"{display} (@{sender_obj['username']})".strip()
    result = await record_inbound(
        db, channel="TELEGRAM", sender=str(chat["id"]), body=text,
        external_message_id=str(msg.get("message_id")) if msg.get("message_id") is not None else None,
        display_name=display or None,
    )
    return {"ok": True, "result": result}


@router.post("/rubika/{secret}")
async def rubika_webhook(secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    configured = get_settings().rubika_webhook_secret
    if not configured or secret != configured:
        raise HTTPException(status_code=401, detail="invalid rubika webhook secret")
    payload = await request.json()
    update = payload.get("update") or {}
    new_message = update.get("new_message") or {}
    chat_id = update.get("chat_id")
    text = new_message.get("text")
    if update.get("type") != "NewMessage" or not chat_id or not text:
        return {"ok": True, "processed": False}
    result = await record_inbound(
        db, channel="RUBIKA", sender=str(chat_id), body=str(text),
        external_message_id=str(new_message.get("message_id")) if new_message.get("message_id") else None,
        display_name=f"Rubika {new_message.get('sender_id') or chat_id}",
    )
    return {"ok": True, "result": result}
