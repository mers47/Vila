from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.entities import User
from app.services.audit import audit
from app.services.outreach import queue_outbound

router = APIRouter(prefix="/outreach", tags=["outreach"])


class SendRequest(BaseModel):
    lead_id: UUID
    contact_id: UUID
    text: str = Field(default="", max_length=4000)
    campaign_id: UUID | None = None
    message_kind: str = Field(default="text", pattern="^(text|template|marketing_template)$")
    template_name: str | None = None
    template_language: str = "fa"
    template_components: list | None = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.message_kind == "text" and not self.text.strip():
            raise ValueError("text is required for text messages")
        if self.message_kind in {"template", "marketing_template"} and not self.template_name:
            raise ValueError("template_name is required for template messages")
        return self


@router.post("/send", status_code=202)
async def send(
    payload: SendRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "marketing", "supervisor")),
):
    key = idempotency_key or f"manual:{uuid4()}"
    message = await queue_outbound(
        db,
        lead_id=payload.lead_id,
        contact_id=payload.contact_id,
        text=payload.text,
        campaign_id=payload.campaign_id,
        message_kind=payload.message_kind,
        template_name=payload.template_name,
        template_language=payload.template_language,
        template_components=payload.template_components,
        idempotency_key=key,
    )
    await audit(
        db,
        action="outreach.queued",
        entity_type="message",
        entity_id=str(message.id),
        actor_user_id=user.id,
        detail={
            "lead_id": str(payload.lead_id),
            "contact_id": str(payload.contact_id),
            "message_kind": payload.message_kind,
            "campaign_id": str(payload.campaign_id) if payload.campaign_id else None,
            "idempotency_key": key,
            "initial_status": message.status,
        },
    )
    await db.commit()
    return {"queued": message.status in {"QUEUED", "RETRYING"}, "message_id": str(message.id), "status": message.status, "idempotency_key": key}
