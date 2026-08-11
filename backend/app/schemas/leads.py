from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class LeadCreate(BaseModel):
    business_name: str
    industry: str | None = None
    city: str | None = None
    province: str | None = None
    website: str | None = None
    source: str = "MANUAL"
    tags: list[str] = []


class LeadResponse(BaseModel):
    id: UUID
    business_name: str
    industry: str | None
    city: str | None
    score: int
    status: str
    temperature: str
    created_at: datetime

    model_config = {"from_attributes": True}