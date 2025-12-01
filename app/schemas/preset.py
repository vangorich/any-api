from typing import Optional, List, Any, Union
from pydantic import BaseModel
from datetime import datetime
from .preset_item import PresetItem

class PresetBase(BaseModel):
    name: str
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0
    content: Optional[Union[str, dict, list]] = None

class PresetCreate(PresetBase):
    pass

class PresetUpdate(PresetBase):
    pass

class Preset(PresetBase):
    id: int
    user_id: int
    creator_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[PresetItem] = []
    content: Optional[Union[str, dict, list]] = None

    class Config:
        from_attributes = True
