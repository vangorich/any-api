from typing import Any, List
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.api import deps
from app.core import security
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate, UserCreate
from app.models.system_config import SystemConfig
from app.schemas.common import PaginatedResponse
from pydantic import EmailStr, ValidationError

router = APIRouter()

@router.get("/", response_model=PaginatedResponse[UserSchema])
async def read_users(
    db: AsyncSession = Depends(deps.get_db),
    page: int = 1,
    size: int = 20,
    q: str = None,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Retrieve users with pagination and search.
    """
    skip = (page - 1) * size
    query = select(User)

    if q:
        # 尝试按ID搜索
        try:
            user_id = int(q)
            query = query.filter(User.id == user_id)
        except ValueError:
            # 按用户名或邮箱模糊搜索
            query = query.filter(
                (User.username.ilike(f"%{q}%")) |
                (User.email.ilike(f"%{q}%"))
            )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    result = await db.execute(query.offset(skip).limit(size))
    users = result.scalars().all()
    
    # 手动将 SQLAlchemy 模型转换为 Pydantic Schema，并处理验证错误
    user_schemas = []
    for user in users:
        try:
            user_schemas.append(UserSchema.from_orm(user))
        except Exception:
            # 如果有脏数据导致验证失败，跳过该用户
            continue
    
    return PaginatedResponse(
        total=total,
        items=user_schemas,
        page=page,
        size=size
    )

@router.post("/create", response_model=UserSchema)
async def create_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Create new user by admin.
    """
    try:
        # 验证输入
        user_create = UserCreate(**user_in.dict())
    except ValidationError as e:
        # Pydantic 验证失败
        first_error = e.errors()[0]
        field = first_error['loc'][0]
        msg = first_error['msg']
        
        # 优化错误信息
        if field == 'username':
            detail = f"用户名验证失败: {msg}"
        elif field == 'password':
            detail = f"密码验证失败: {msg}"
        elif field == 'email':
            detail = "邮箱格式不正确"
        else:
            detail = "输入验证失败"
            
        raise HTTPException(
            status_code=422,
            detail=detail,
        )

    # 检查 email 是否已存在
    result = await db.execute(select(User).filter(User.email == user_create.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该邮箱已被注册",
        )
        
    # 检查 username 是否已存在
    result = await db.execute(select(User).filter(User.username == user_create.username))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该用户名已被使用",
        )
        
    
    user = User(
        email=user_create.email,
        username=user_create.username,
        password_hash=security.get_password_hash(user_create.password),
        is_active=True,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/me", response_model=UserSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    password: str = Body(None),
    old_password: str = Body(None),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    if password:
        if not old_password:
            raise HTTPException(status_code=400, detail="修改密码需要提供旧密码")
        if not security.verify_password(old_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="旧密码错误")
        current_user.password_hash = security.get_password_hash(password)
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.get("/me", response_model=UserSchema)
async def read_user_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.post("/open", response_model=UserSchema)
async def create_user_open(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate,
    _: dict = Depends(deps.verify_turnstile)
) -> Any:
    """
    Create new user without login.
    """
    # 检查系统设置
    system_config_result = await db.execute(select(SystemConfig))
    system_config = system_config_result.scalars().first()

    if not system_config or not system_config.allow_registration:
        raise HTTPException(status_code=403, detail="系统当前未开放注册")

    # 邮箱白名单验证
    if system_config and system_config.email_whitelist_enabled:
        domain = user_in.email.split('@')[-1]
        
        # 从JSON字符串解析白名单
        import json
        try:
            allowed_domains = json.loads(system_config.email_whitelist)
        except (json.JSONDecodeError, TypeError):
            allowed_domains = [] # 解析失败则视为空列表

        if domain not in allowed_domains:
            allowed_domains_str = ", ".join(allowed_domains)
            raise HTTPException(
                status_code=400,
                detail=f"该邮箱后缀不允许注册。请使用以下后缀的邮箱: {allowed_domains_str}",
            )
    try:
        user_create = UserCreate(**user_in.dict())
    except ValidationError as e:
        first_error = e.errors()[0]
        field = first_error['loc'][0]
        msg = first_error['msg']
        
        if field == 'username':
            detail = f"用户名验证失败: {msg}"
        elif field == 'password':
            detail = f"密码验证失败: {msg}"
        elif field == 'email':
            detail = "邮箱格式不正确"
        else:
            detail = "输入验证失败"
            
        raise HTTPException(
            status_code=422,
            detail=detail,
        )

    result = await db.execute(select(User).filter(User.email == user_create.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该邮箱已被注册",
        )
        
    result = await db.execute(select(User).filter(User.username == user_create.username))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="该用户名已被使用",
        )
        
    user = User(
        email=user_create.email,
        username=user_create.username,
        password_hash=security.get_password_hash(user_create.password),
        is_active=True,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/{user_id}/toggle-active", response_model=UserSchema)
async def toggle_user_active(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Toggle user active status (enable/disable).
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
    
    user.is_active = not user.is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", response_model=UserSchema)
async def delete_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Delete (deactivate) user.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # 软删除：设置为不活跃
    user.is_active = False
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Update a user.
    """
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )

    # 安全检查：防止最后一个 super_admin 降级自己
    if current_user.id == user_id and user.role == "super_admin" and user_in.role != "super_admin":
        # 查询是否还有其他 super_admin
        count_query = select(func.count(User.id)).filter(User.role == "super_admin", User.id != user_id)
        other_super_admins = await db.scalar(count_query)
        if other_super_admins == 0:
            raise HTTPException(
                status_code=403,
                detail="系统中必须至少保留一名超级管理员",
            )
            
    # 更新字段
    update_data = user_in.dict(exclude_unset=True)
    
    # 只有 super_admin 才能修改权限
    if "role" in update_data and current_user.role != "super_admin":
        del update_data["role"]
        
    if "password" in update_data and update_data["password"]:
        user.password_hash = security.get_password_hash(update_data["password"])
        del update_data["password"] # 从待更新字典中移除，避免直接赋值
    
    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

