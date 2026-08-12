from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class CampaignCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    min_score: int = Field(default=60, ge=0, le=100)
    channels: list[str]
    message_template: str = Field(min_length=1, max_length=4000)
    provider_templates: dict = Field(default_factory=dict)
    follow_up_rules: dict = Field(default_factory=dict)

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: list[str]) -> list[str]:
        allowed = {"WHATSAPP", "INSTAGRAM", "TELEGRAM", "EITAA", "RUBIKA"}
        normalized = list(dict.fromkeys(str(item).strip().upper() for item in value if str(item).strip()))
        if not normalized:
            raise ValueError("at least one channel is required")
        unknown = sorted(set(normalized) - allowed)
        if unknown:
            raise ValueError(f"unsupported channels: {', '.join(unknown)}")
        return normalized


class CampaignOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    status: str
    min_score: int
    channels: list
    message_template: str
    provider_templates: dict
