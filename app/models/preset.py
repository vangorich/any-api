from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Preset(Base):
    __tablename__ = "presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=True) # 添加 content 字段
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    creator_username = Column(String, nullable=True)  # 创建者用户名（用于溯源）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 最新修改时间

    user = relationship("User")
    regex_rules = relationship("PresetRegexRule", back_populates="preset", cascade="all, delete-orphan")
    items = relationship("PresetItem", cascade="all, delete-orphan", order_by="PresetItem.sort_order")

