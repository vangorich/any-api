from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class PresetRegexRuleBase(BaseModel):
    """预设内部正则规则基础Schema"""
    name: str
    pattern: str
    replacement: str
    type: str  # "pre" or "post"
    is_active: Optional[bool] = True
    sort_order: Optional[int] = 0

class PresetRegexRuleCreate(PresetRegexRuleBase):
    """创建预设内部正则规则Schema"""
    pass

class PresetRegexRuleUpdate(PresetRegexRuleBase):
    """更新预设内部正则规则Schema"""
    pass

class PresetRegexRule(PresetRegexRuleBase):
    """预设内部正则规则完整Schema"""
    id: int
    preset_id: int
    creator_username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
