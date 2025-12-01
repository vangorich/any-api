import json
import logging
from typing import Any, List
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api import deps
from app.models.preset import Preset
from app.models.preset_item import PresetItem
from app.models.user import User
from app.schemas.preset import Preset as PresetSchema, PresetCreate, PresetUpdate
from app.schemas.preset_item import PresetItem as PresetItemSchema, PresetItemCreate, PresetItemUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[PresetSchema])
async def read_presets(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve presets.
    """
    query = select(Preset).filter(Preset.user_id == current_user.id).order_by(Preset.sort_order).options(selectinload(Preset.items))
    result = await db.execute(query.offset(skip).limit(limit))
    presets = result.scalars().unique().all()
    
    # 立即字符串化方案
    results = []
    for preset in presets:
        items = []
        # 确保按 sort_order 排序
        sorted_items = sorted(preset.items, key=lambda x: x.sort_order)
        for item in sorted_items:
            items.append({
                "id": item.id,
                "preset_id": item.preset_id,
                "role": item.role,
                "type": item.type,
                "name": item.name,
                "content": item.content,
                "sort_order": item.sort_order,
                "enabled": item.enabled,
                "creator_username": item.creator_username,
                "created_at": item.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
                "updated_at": item.updated_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
            })

        results.append({
            "id": preset.id,
            "name": preset.name,
            "is_active": preset.is_active,
            "sort_order": preset.sort_order,
            "user_id": preset.user_id,
            "creator_username": preset.creator_username,
            "content": preset.content,
            "created_at": preset.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
            "updated_at": preset.updated_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
            "items": items,
        })
    return results

@router.post("/", response_model=PresetSchema)
async def create_preset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_in: PresetCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new preset.
    """
    # 确保 content 是 JSON 字符串
    content = preset_in.content
    if content is not None and not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    preset = Preset(
        name=preset_in.name,
        user_id=current_user.id,
        is_active=preset_in.is_active,
        sort_order=preset_in.sort_order,
        creator_username=current_user.username,  # 自动设置创建者用户名
        content=content,
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    
    # 手动构建响应模型以避免验证错误
    return PresetSchema(
        id=preset.id,
        name=preset.name,
        is_active=preset.is_active,
        sort_order=preset.sort_order,
        user_id=preset.user_id,
        creator_username=preset.creator_username,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
        content=preset.content,
        items=[] # 新创建的预设还没有items
    )

@router.put("/{preset_id}", response_model=PresetSchema)
async def update_preset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_id: int,
    preset_in: PresetUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update preset.
    """
    result = await db.execute(select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id))
    preset = result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    preset_data = preset_in.dict(exclude_unset=True)
    for key, value in preset_data.items():
        if value is not None:
            # 确保 content 是 JSON 字符串
            if key == 'content' and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            setattr(preset, key, value)
    
    db.add(preset)
    await db.commit()

    # Re-fetch the preset with items loaded to satisfy the response model
    query = select(Preset).options(selectinload(Preset.items)).filter(Preset.id == preset_id)
    result = await db.execute(query)
    preset = result.scalars().unique().first()
    return preset

@router.delete("/{preset_id}", response_model=PresetSchema)
async def delete_preset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete preset.
    """
    result = await db.execute(select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id))
    preset = result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    await db.delete(preset)
    await db.commit()
    return preset


# Preset Items

@router.post("/{preset_id}/items/", response_model=PresetItemSchema)
async def create_preset_item(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_id: int,
    item_in: PresetItemCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new preset item for a preset.
    """
    result = await db.execute(select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id))
    preset = result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    item = PresetItem(
        **item_in.dict(),
        preset_id=preset_id,
        creator_username=current_user.username,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.put("/{preset_id}/items/{item_id}", response_model=PresetItemSchema)
async def update_preset_item(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_id: int,
    item_id: int,
    item_in: PresetItemUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a preset item.
    """
    result = await db.execute(
        select(PresetItem)
        .join(Preset)
        .filter(PresetItem.id == item_id, PresetItem.preset_id == preset_id, Preset.user_id == current_user.id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Preset item not found")
        
    update_data = item_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
        
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{preset_id}/items/{item_id}", response_model=PresetItemSchema)
async def delete_preset_item(
    *,
    db: AsyncSession = Depends(deps.get_db),
    preset_id: int,
    item_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a preset item.
    """
    result = await db.execute(
        select(PresetItem)
        .join(Preset)
        .filter(PresetItem.id == item_id, PresetItem.preset_id == preset_id, Preset.user_id == current_user.id)
    )
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Preset item not found")
        
    await db.delete(item)
    await db.commit()
    return item
