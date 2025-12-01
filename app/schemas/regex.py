from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class RegexRuleBase(BaseModel):
    name: str
    pattern: str
    replacement: str
    type: str # "pre" or "post"
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0

class RegexRuleCreate(RegexRuleBase):
    pass

class RegexRuleUpdate(RegexRuleBase):
    pass

class RegexRule(RegexRuleBase):
    id: int
    user_id: int
    creator_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
