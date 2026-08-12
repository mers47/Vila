from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ContactIn(BaseModel):
    channel: str
    value: str
    consent_status: str = "UNKNOWN"
    consent_source: str | None = None


class LeadCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    industry: str | None = None
    province: str | None = None
    city: str | None = None
    address: str | None = None
    website: str | None = None
    source: str
    source_external_id: str | None = None
    contacts: list[ContactIn] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata_json: dict = Field(default_factory=dict)


class LeadOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    business_name: str
    industry: str | None
    province: str | None
    city: str | None
    source: str
    score: int
    status: str
    temperature: str
    created_at: datetime
