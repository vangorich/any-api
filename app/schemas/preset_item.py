from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PresetItemBase(BaseModel):
    name: str
    role: str
    type: str
    content: str
    enabled: Optional[bool] = True
    sort_order: Optional[int] = 0

class PresetItemCreate(PresetItemBase):
    pass

class PresetItemUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None

class PresetItem(PresetItemBase):
    id: int
    preset_id: int
    creator_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True