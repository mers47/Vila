from pydantic import BaseModel
from uuid import UUID


class CampaignCreate(BaseModel):
    name: str
    min_score: int = 60
    channels: list[str]
    message_template: str
    follow_up_rules: dict = {}


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    status: str
    min_score: int
    channels: list
    message_template: str
    created_at: str

    model_config = {"from_attributes": True}