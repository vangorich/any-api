from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.core.database import Base

class PresetItem(Base):
    __tablename__ = "preset_items"

    id = Column(Integer, primary_key=True, index=True)
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=False)
    
    # 预设条目内容
    name = Column(String, nullable=False, default="新条目")
    role = Column(String, nullable=False, default="user") # system, user, assistant
    type = Column(String, nullable=False, default="normal") # normal, user_input
    content = Column(Text, nullable=False, default="")
    
    # 元数据
    enabled = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    creator_username = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
