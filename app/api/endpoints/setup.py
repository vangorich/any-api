from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.database import Base, engine
from app.models.user import User
from app.models.system_config import SystemConfig

router = APIRouter()


class SetupStatus(BaseModel):
    """初始化状态响应"""
    needs_setup: bool
    database_type: str


class InitializeRequest(BaseModel):
    """初始化请求"""
    username: str
    password: str
    confirm_password: str
    database_confirmed: bool = False


@router.get("/status", response_model=SetupStatus)
async def get_setup_status(
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    检查系统是否需要初始化
    
    返回:
    - needs_setup: 是否需要初始化 (检查是否存在管理员账户)
    - database_type: 数据库类型 (sqlite/postgresql/mysql)
    """
    # 检查是否存在管理员账户
    result = await db.execute(
        select(User).filter(User.role == "super_admin")
    )
    admin_user = result.scalars().first()
    
    # 判断数据库类型
    database_url = settings.DATABASE_URL.lower()
    if "sqlite" in database_url:
        db_type = "sqlite"
    elif "postgresql" in database_url or "asyncpg" in database_url:
        db_type = "postgresql"
    elif "mysql" in database_url or "aiomysql" in database_url:
        db_type = "mysql"
    else:
        db_type = "unknown"
    
    return {
        "needs_setup": admin_user is None,
        "database_type": db_type
    }


@router.post("/initialize")
async def initialize_system(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: InitializeRequest,
) -> Any:
    """
    执行系统初始化
    
    步骤:
    1. 验证是否已初始化
    2. 验证密码一致性
    3. 检查 SQLite 确认状态
    4. 创建管理员账户
    5. 初始化系统配置
    """
    # 1. 检查是否已存在管理员账户
    result = await db.execute(
        select(User).filter(User.role == "super_admin")
    )
    admin_user = result.scalars().first()
    
    if admin_user:
        raise HTTPException(
            status_code=400,
            detail="系统已初始化,管理员账户已存在"
        )
    
    # 2. 验证密码一致性
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="两次输入的密码不一致"
        )
    
    # 3. 验证密码长度
    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="密码长度至少为 6 位"
        )
    
    # 4. 检查用户名是否已存在
    result = await db.execute(
        select(User).filter(User.username == request.username)
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="用户名已存在"
        )
    
    # 5. 如果是 SQLite 且未确认,返回提示
    database_url = settings.DATABASE_URL.lower()
    if "sqlite" in database_url and not request.database_confirmed:
        return {
            "status": "confirmation_required",
            "message": "检测到您正在使用 SQLite 数据库。SQLite 适合小规模部署和测试环境,但不推荐用于生产环境。是否继续?",
            "database_type": "sqlite"
        }
    
    try:
        # 6. 确保所有数据库表已创建
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 7. 创建管理员账户
        admin_user = User(
            username=request.username,
            email=f"{request.username}@example.com",  # 默认邮箱
            password_hash=security.get_password_hash(request.password),
            is_active=True,
            role="super_admin"
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        # 8. 初始化系统配置 (如果不存在)
        config_result = await db.execute(select(SystemConfig))
        system_config = config_result.scalars().first()
        
        if not system_config:
            system_config = SystemConfig(
                site_name="Any API",
                allow_registration=True,
                allow_password_login=True,
            )
            db.add(system_config)
            await db.commit()
        
        return {
            "status": "success",
            "message": "系统初始化成功",
            "admin_username": request.username
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"初始化失败: {str(e)}"
        )
