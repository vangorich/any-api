from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PresetRegexRule(Base):
    """预设内部正则规则模型"""
    __tablename__ = "preset_regex_rules"

    id = Column(Integer, primary_key=True, index=True)
    preset_id = Column(Integer, ForeignKey("presets.id", ondelete="CASCADE"), nullable=False)  # 所属预设ID
    name = Column(String, nullable=False)
    pattern = Column(String, nullable=False)
    replacement = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "pre" or "post"
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    creator_username = Column(String, nullable=True)  # 创建者用户名（用于溯源）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 最新修改时间

    preset = relationship("Preset", back_populates="regex_rules")
