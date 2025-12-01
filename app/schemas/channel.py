from typing import Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

# Channel Schemas
class ChannelBase(BaseModel):
    name: str
    type: str  # gemini, openai, claude, etc.
    api_url: str

class ChannelCreate(ChannelBase):
    pass

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    api_url: Optional[str] = None

class Channel(ChannelBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
