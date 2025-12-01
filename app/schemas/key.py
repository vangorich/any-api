from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

# Official Key Schemas
class OfficialKeyBase(BaseModel):
    key: str
    is_active: Optional[bool] = True
    channel_id: Optional[int] = None

class OfficialKeyCreate(OfficialKeyBase):
    pass

class OfficialKeyBatchCreate(BaseModel):
    keys: List[str]
    is_active: Optional[bool] = True
    channel_id: Optional[int] = None

class OfficialKeyUpdate(BaseModel):
    is_active: Optional[bool] = None
    key: Optional[str] = None
    channel_id: Optional[int] = None

class OfficialKey(OfficialKeyBase):
    id: int
    user_id: int
    usage_count: int
    error_count: int
    total_tokens: int
    last_status: str
    last_status_code: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Exclusive Key Schemas
class ExclusiveKeyBase(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = True
    preset_id: Optional[int] = None
    channel_id: Optional[int] = None
    enable_regex: Optional[bool] = False

class ExclusiveKeyCreate(ExclusiveKeyBase):
    pass

class ExclusiveKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    preset_id: Optional[int] = None
    channel_id: Optional[int] = None
    enable_regex: Optional[bool] = None

class ExclusiveKey(ExclusiveKeyBase):
    id: int
    key: str
    user_id: int
    created_at: datetime
    preset_id: Optional[int] = None
    channel_id: Optional[int] = None
    enable_regex: Optional[bool] = False

    class Config:
        from_attributes = True
