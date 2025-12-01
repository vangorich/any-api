from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api import deps
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.models.verification_code import VerificationCode
from app.models.system_config import SystemConfig
from app.models.ip_blacklist import IPBlacklist
from app.schemas.token import Token
from app.schemas.verification_code import SendCodeRequest, VerifyCodeRequest, ResetPasswordRequest
from app.services.email_service import email_service
from app.services.captcha_service import captcha_service

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: dict = Depends(deps.verify_turnstile)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # 获取系统配置
    config_result = await db.execute(select(SystemConfig).filter(SystemConfig.id == 1))
    system_config = config_result.scalars().first()

    # Authenticate user - 支持用户名或邮箱登录
    result = await db.execute(
        select(User).filter(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")
        
    # 检查是否允许密码登录
    if system_config and not system_config.allow_password_login:
        if user.role == "user":
            raise HTTPException(status_code=403, detail="密码登录功能已对普通用户关闭")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/send-code")
async def send_verification_code(
    *,
    db: AsyncSession = Depends(deps.get_db),
    send_request: SendCodeRequest,
    fastapi_request: Request,
    _: dict = Depends(deps.verify_turnstile),
    __ : dict = Depends(deps.verify_captcha)
) -> Any:
    """
    发送验证码到邮箱
    
    - **email**: 邮箱地址
    - **type**: 验证码类型 (register/reset_password)
    """
    # 获取系统配置
    config_result = await db.execute(select(SystemConfig).filter(SystemConfig.id == 1))
    system_config = config_result.scalars().first()

    if system_config.enable_ip_rate_limit:
        # 获取客户端IP
        ip_address = fastapi_request.headers.get("X-Forwarded-For") or fastapi_request.client.host
        
        # IP频率和黑名单检查
        ip_record_result = await db.execute(select(IPBlacklist).filter(IPBlacklist.ip_address == ip_address))
        ip_record = ip_record_result.scalars().first()

        if not ip_record:
            ip_record = IPBlacklist(ip_address=ip_address)
            db.add(ip_record)
        
        ip_record.reset_if_new_day()
        
        # 检查每日发送上限
        if ip_record.email_sent_count >= 10:
            raise HTTPException(status_code=429, detail="今日邮件发送次数已达上限")

        # 动态冷却时间
        cooldown_times = {
            0: 0, 1: 60, 2: 300, 3: 600, 4: 1800
        }
        wait_time = cooldown_times.get(ip_record.email_sent_count, 3600) # 超过4次后每次等待1小时
        
        if ip_record.last_email_sent_at and datetime.now(timezone.utc) < ip_record.last_email_sent_at.replace(tzinfo=timezone.utc) + timedelta(seconds=wait_time):
            remaining_time = (ip_record.last_email_sent_at.replace(tzinfo=timezone.utc) + timedelta(seconds=wait_time) - datetime.now(timezone.utc)).seconds
            raise HTTPException(status_code=429, detail=f"请求过于频繁，请在 {remaining_time} 秒后重试")
    
    if not system_config:
        raise HTTPException(status_code=500, detail="未找到系统配置")

    # 如果是注册请求，检查是否允许注册
    if send_request.type == "register":
        if not system_config.allow_registration:
            raise HTTPException(status_code=403, detail="系统当前未开放注册")
        if not system_config.require_email_verification:
            raise HTTPException(status_code=403, detail="系统未开启邮箱验证")

        # 注册类型验证码：检查邮箱是否已被注册
        existing_user = await db.execute(select(User).filter(User.email == send_request.email))
        if existing_user.scalars().first():
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
    
    # 邮箱格式和白名单验证
    if not send_request.email or '@' not in send_request.email:
        raise HTTPException(status_code=400, detail="无效的邮箱地址")
        
    if system_config.email_whitelist_enabled:
        domain = send_request.email.split('@')[1]
        whitelist = system_config.email_whitelist or []
        if domain not in whitelist:
            raise HTTPException(status_code=403, detail="该邮箱域名不被允许")
    
    # 生成验证码
    code = VerificationCode.generate_code()
    verification_code = VerificationCode(
        email=send_request.email,
        code=code,
        type=send_request.type,
        expires_at=VerificationCode.get_expiration_time()
    )
    db.add(verification_code)
    
    # 如果开启了IP限制，则更新IP记录
    if system_config.enable_ip_rate_limit and 'ip_record' in locals():
        ip_record.email_sent_count += 1
        ip_record.last_email_sent_at = datetime.now(timezone.utc)
        db.add(ip_record)

    await db.commit()
    
    # 配置并发送邮件
    await email_service.configure(system_config)
    
    if not email_service.is_configured():
        raise HTTPException(status_code=500, detail="邮件服务未配置")
    
    try:
        if send_request.type == "register":
            success = await email_service.send_verification_email(
                send_request.email,
                code,
                system_config.site_name or "Any API"
            )
        else:  # reset_password
            # 查找用户以获取用户名
            user_result = await db.execute(select(User).filter(User.email == send_request.email))
            user = user_result.scalars().first()
            username = user.username if user else None
            
            success = await email_service.send_password_reset_email(
                send_request.email,
                code,
                system_config.site_name or "Any API",
                username=username
            )
        
        if not success:
            raise Exception("发送邮件失败")
            
        return {"message": "验证码已发送", "expires_in": 300}  # 5 minutes
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"发送邮件失败: {str(e)}")

@router.post("/verify-code")
async def verify_code(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: VerifyCodeRequest
) -> Any:
    """
    验证验证码
    
    - **email**: 邮箱地址
    - **code**: 验证码
    - **type**: 验证码类型
    """
    # 查找验证码
    result = await db.execute(
        select(VerificationCode).filter(
            VerificationCode.email == request.email,
            VerificationCode.code == request.code,
            VerificationCode.type == request.type,
            VerificationCode.is_used == False
        ).order_by(VerificationCode.created_at.desc())
    )
    verification_code = result.scalars().first()
    
    if not verification_code:
        raise HTTPException(status_code=400, detail="无效的验证码")
    
    if verification_code.is_expired():
        raise HTTPException(status_code=400, detail="验证码已过期")
    
    # 标记为已使用
    verification_code.is_used = True
    await db.commit()
    
    return {"message": "验证成功", "email": request.email}

@router.post("/reset-password")
async def reset_password(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: ResetPasswordRequest,
    _: dict = Depends(deps.verify_turnstile)
) -> Any:
    """
    重置密码
    
    - **email_or_username**: 邮箱地址或用户名
    - **code**: 验证码
    - **new_password**: 新密码
    """
    # 获取系统配置
    config_result = await db.execute(select(SystemConfig).filter(SystemConfig.id == 1))
    system_config = config_result.scalars().first()
    
    if not system_config:
        raise HTTPException(status_code=500, detail="未找到系统配置")
    
    # 检查是否开启邮箱验证功能
    if not system_config.require_email_verification:
        raise HTTPException(status_code=403, detail="系统未开启邮箱验证")
    
    # 验证邮箱格式及白名单 (与注册逻辑一致)
    if not request.email or '@' not in request.email:
        raise HTTPException(status_code=400, detail="无效的邮箱地址")
    
    if system_config.email_whitelist_enabled:
        domain = request.email.split('@')[1]
        whitelist = system_config.email_whitelist or []
        if domain not in whitelist:
            raise HTTPException(status_code=403, detail="该邮箱域名不被允许")

    # 查找用户（只通过邮箱）
    user_result = await db.execute(
        select(User).filter(User.email == request.email)
    )
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 验证验证码
    code_result = await db.execute(
        select(VerificationCode).filter(
            VerificationCode.email == user.email,
            VerificationCode.code == request.code,
            VerificationCode.type == "reset_password",
            VerificationCode.is_used == False
        ).order_by(VerificationCode.created_at.desc())
    )
    verification_code = code_result.scalars().first()
    
    if not verification_code:
        raise HTTPException(status_code=400, detail="无效的验证码")
    
    if verification_code.is_expired():
        raise HTTPException(status_code=400, detail="验证码已过期")
    
    # 更新密码
    user.password_hash = security.get_password_hash(request.new_password)
    
    # 标记验证码为已使用
    verification_code.is_used = True
    
    db.add(user)
    await db.commit()
    
    return {"message": "密码重置成功"}

