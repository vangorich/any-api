from typing import Optional
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timezone
import re

class UserBase(BaseModel):
    email: str
    username: str
    is_active: Optional[bool] = True
    role: Optional[str] = "user" # "user", "admin", "super_admin"

class UserCreate(UserBase):
    password: str
    turnstile_token: Optional[str] = None

    @validator('email')
    def validate_email(cls, v):
        if not v:
            raise ValueError("邮箱不能为空")
        
        parts = v.split('@')
        if len(parts) != 2:
            raise ValueError("邮箱必须包含一个 @ 符号")

        local_part, domain_part = parts
        if not re.match(r'^[a-zA-Z0-9]+$', local_part):
            raise ValueError("@ 符号前的部分只能包含字母和数字")

        if '.' not in domain_part:
            raise ValueError("邮箱域名必须包含 . 符号")
            
        domain_name, top_level_domain = domain_part.rsplit('.', 1)
        if not re.match(r'^[a-zA-Z]+$', domain_name):
            raise ValueError("@ 和 . 符号之间的部分只能包含字母")
        if not re.match(r'^[a-zA-Z.]+$', top_level_domain):
            raise ValueError(". 符号后的部分只能包含字母")
            
        return v

    @validator('username')
    def validate_username(cls, v):
        if len(v) < 4:
            raise ValueError('用户名长度不能少于4位')
        if not re.match(r'^[a-zA-Z0-9]+$', v):
            raise ValueError('用户名只能包含字母和数字')
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度不能少于6位')
        if re.match(r'^\d+$', v):
            raise ValueError('密码不能为纯数字')
        # 补充：密码必须包含字母
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含英文字母')
        return v

class UserUpdate(UserBase):
    password: Optional[str] = None

    @validator('password')
    def validate_password(cls, v):
        if v is None:
            return v
        if len(v) < 6:
            raise ValueError('密码长度不能少于6位')
        if re.match(r'^\d+$', v):
            raise ValueError('密码不能为纯数字')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含英文字母')
        return v

class UserInDBBase(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        }

class User(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str
