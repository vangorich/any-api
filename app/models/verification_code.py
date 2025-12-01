from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from datetime import datetime, timedelta, timezone
from app.core.database import Base

class VerificationCode(Base):
    """邮箱验证码模型"""
    __tablename__ = "verification_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)  # 邮箱地址
    code = Column(String(6), nullable=False)  # 6位验证码
    type = Column(String, nullable=False)  # register, reset_password
    is_used = Column(Boolean, default=False)  # 是否已使用
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 过期时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        # 确保 expires_at 有时区信息
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            # 如果没有时区信息，假定为 UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at
    
    def is_valid(self) -> bool:
        """检查是否有效（未使用且未过期）"""
        return not self.is_used and not self.is_expired()
    
    @staticmethod
    def generate_code() -> str:
        """生成6位数字验证码"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    @staticmethod
    def get_expiration_time() -> datetime:
        """获取过期时间（10分钟后）"""
        return datetime.now(timezone.utc) + timedelta(minutes=10)
