from sqlalchemy import Column, String, Integer, DateTime, Date, func
from app.core.database import Base
import datetime

class IPBlacklist(Base):
    """
    IP黑名单和邮件发送频率限制模型
    """
    __tablename__ = 'ip_blacklist'

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, index=True, nullable=False)
    
    # 每日邮件发送计数
    email_sent_count = Column(Integer, default=0)
    last_email_sent_date = Column(Date, default=datetime.date.today)
    
    # 用于动态冷却
    last_email_sent_at = Column(DateTime, default=func.now())

    def reset_if_new_day(self):
        """如果新的一天，重置每日计数"""
        if self.last_email_sent_date != datetime.date.today():
            self.last_email_sent_date = datetime.date.today()
            self.email_sent_count = 0