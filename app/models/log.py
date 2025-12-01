from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    exclusive_key_id = Column(Integer, ForeignKey("exclusive_keys.id"), nullable=True)
    official_key_id = Column(Integer, ForeignKey("official_keys.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    model = Column(String, nullable=False)
    status = Column(String, nullable=False) # "ok", "error"
    status_code = Column(Integer, nullable=True)
    latency = Column(Float, default=0.0) # Total time in seconds
    ttft = Column(Float, default=0.0) # Time to first token
    is_stream = Column(Boolean, default=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    exclusive_key = relationship("ExclusiveKey")
    official_key = relationship("OfficialKey")
    user = relationship("User")
