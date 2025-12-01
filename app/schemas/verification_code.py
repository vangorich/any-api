from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VerificationCodeBase(BaseModel):
    """验证码基础schema"""
    email: str
    code: str
    type: str  # register, reset_password

class VerificationCodeCreate(VerificationCodeBase):
    """创建验证码"""
    pass

class VerificationCodeInDB(VerificationCodeBase):
    """数据库中的验证码"""
    id: int
    is_used: bool
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    email: str
    type: str = "register"  # register, reset_password
    captcha_id: Optional[str] = None
    captcha_code: Optional[str] = None

class VerifyCodeRequest(BaseModel):
    """验证验证码请求"""
    email: str
    code: str
    type: str = "register"

class ResetPasswordRequest(BaseModel):
    """密码重置请求"""
    email: str
    code: str
    new_password: str

class CaptchaVerifyRequest(BaseModel):
    """图形验证码预验证请求"""
    captcha_id: str
    captcha_code: str

