from sqlalchemy import Column, String, DateTime
from app.core.database import Base
from datetime import datetime, timedelta

class Captcha(Base):
    __tablename__ = 'captchas'
    
    id = Column(String, primary_key=True, index=True)
    code = Column(String)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=5))

    def is_expired(self):
        return datetime.utcnow() > self.expires_at