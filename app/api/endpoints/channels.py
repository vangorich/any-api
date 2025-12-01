from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from app.api import deps
from app.models.user import User
from app.models.channel import Channel as ChannelModel
from app.models.key import OfficialKey
from app.schemas.channel import Channel as ChannelSchema, ChannelCreate, ChannelUpdate

router = APIRouter()

@router.get("/", response_model=List[ChannelSchema])
async def read_channels(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取当前用户的渠道列表, 包含聚合的密钥统计信息
    """
    subquery = (
        select(
            OfficialKey.channel_id,
            func.count(OfficialKey.id).label("total_keys"),
            func.sum(case((OfficialKey.is_active, 1), else_=0)).label("active_keys"),
            func.sum(OfficialKey.usage_count).label("usage_count"),
            func.sum(OfficialKey.error_count).label("error_count"),
            func.sum(OfficialKey.input_tokens).label("input_tokens"),
            func.sum(OfficialKey.output_tokens).label("output_tokens")
        )
        .group_by(OfficialKey.channel_id)
        .subquery()
    )

    stmt = (
        select(
            ChannelModel,
            func.coalesce(subquery.c.total_keys, 0).label("total_keys"),
            func.coalesce(subquery.c.active_keys, 0).label("active_keys"),
            func.coalesce(subquery.c.usage_count, 0).label("usage_count"),
            func.coalesce(subquery.c.error_count, 0).label("error_count"),
            func.coalesce(subquery.c.input_tokens, 0).label("input_tokens"),
            func.coalesce(subquery.c.output_tokens, 0).label("output_tokens")
        )
        .outerjoin(subquery, ChannelModel.id == subquery.c.channel_id)
        .where(ChannelModel.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    
    channels_data = []
    for channel, total_keys, active_keys, usage_count, error_count, input_tokens, output_tokens in result.all():
        channel_dict = channel.__dict__
        channel_dict["total_keys"] = total_keys
        channel_dict["active_keys"] = active_keys
        channel_dict["usage_count"] = usage_count
        channel_dict["error_count"] = error_count
        channel_dict["input_tokens"] = input_tokens
        channel_dict["output_tokens"] = output_tokens
        channels_data.append(channel_dict)
        
    return channels_data

@router.post("/", response_model=ChannelSchema)
async def create_channel(
    *,
    db: AsyncSession = Depends(deps.get_db),
    channel_in: ChannelCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建新渠道
    """
    channel = ChannelModel(
        name=channel_in.name,
        type=channel_in.type,
        api_url=channel_in.api_url,
        user_id=current_user.id
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel

@router.patch("/{channel_id}", response_model=ChannelSchema)
async def update_channel(
    *,
    db: AsyncSession = Depends(deps.get_db),
    channel_id: int,
    channel_in: ChannelUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新渠道信息
    """
    result = await db.execute(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.user_id == current_user.id
        )
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    
    update_data = channel_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)
    
    await db.commit()
    await db.refresh(channel)
    return channel

@router.delete("/{channel_id}")
async def delete_channel(
    *,
    db: AsyncSession = Depends(deps.get_db),
    channel_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除渠道
    """
    result = await db.execute(
        select(ChannelModel).where(
            ChannelModel.id == channel_id,
            ChannelModel.user_id == current_user.id
        )
    )
    channel = result.scalar_one_or_none()
    
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    
    # Unlink official keys
    result = await db.execute(
        select(OfficialKey).where(OfficialKey.channel_id == channel_id)
    )
    for key in result.scalars().all():
        key.channel_id = None
        key.is_active = False # Deactivate key when channel is deleted
        
    await db.delete(channel)
    await db.commit()
    
    return {"message": "渠道已删除"}
