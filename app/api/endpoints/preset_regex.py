from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api import deps
from app.models.preset_regex import PresetRegexRule
from app.models.preset import Preset
from app.models.user import User
from app.schemas.preset_regex import (
    PresetRegexRule as PresetRegexRuleSchema,
    PresetRegexRuleCreate,
    PresetRegexRuleUpdate
)

router = APIRouter()

@router.get("/presets/{preset_id}/regex/", response_model=List[PresetRegexRuleSchema])
async def read_preset_regex_rules(
    preset_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    获取指定预设的所有正则规则
    """
    # 验证预设是否存在且属于当前用户
    preset_result = await db.execute(
        select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id)
    )
    preset = preset_result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # 获取预设的正则规则
    query = select(PresetRegexRule).filter(
        PresetRegexRule.preset_id == preset_id
    ).order_by(PresetRegexRule.sort_order)
    result = await db.execute(query)
    rules = result.scalars().all()
    return rules

@router.post("/presets/{preset_id}/regex/", response_model=PresetRegexRuleSchema)
async def create_preset_regex_rule(
    *,
    preset_id: int,
    db: AsyncSession = Depends(deps.get_db),
    rule_in: PresetRegexRuleCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    为指定预设创建新的正则规则
    """
    # 验证预设是否存在且属于当前用户
    preset_result = await db.execute(
        select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id)
    )
    preset = preset_result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # 创建正则规则
    rule = PresetRegexRule(
        preset_id=preset_id,
        name=rule_in.name,
        pattern=rule_in.pattern,
        replacement=rule_in.replacement,
        type=rule_in.type,
        is_active=rule_in.is_active,
        sort_order=rule_in.sort_order,
        creator_username=current_user.username,  # 自动设置创建者用户名
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/presets/{preset_id}/regex/{rule_id}", response_model=PresetRegexRuleSchema)
async def update_preset_regex_rule(
    *,
    preset_id: int,
    rule_id: int,
    db: AsyncSession = Depends(deps.get_db),
    rule_in: PresetRegexRuleUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    更新预设的正则规则
    """
    # 验证预设是否存在且属于当前用户
    preset_result = await db.execute(
        select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id)
    )
    preset = preset_result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # 获取正则规则
    result = await db.execute(
        select(PresetRegexRule).filter(
            PresetRegexRule.id == rule_id,
            PresetRegexRule.preset_id == preset_id
        )
    )
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # 更新规则
    rule.name = rule_in.name
    rule.pattern = rule_in.pattern
    rule.replacement = rule_in.replacement
    rule.type = rule_in.type
    rule.is_active = rule_in.is_active
    rule.sort_order = rule_in.sort_order
    # updated_at会自动更新
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/presets/{preset_id}/regex/{rule_id}", response_model=PresetRegexRuleSchema)
async def delete_preset_regex_rule(
    *,
    preset_id: int,
    rule_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    删除预设的正则规则
    """
    # 验证预设是否存在且属于当前用户
    preset_result = await db.execute(
        select(Preset).filter(Preset.id == preset_id, Preset.user_id == current_user.id)
    )
    preset = preset_result.scalars().first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # 获取正则规则
    result = await db.execute(
        select(PresetRegexRule).filter(
            PresetRegexRule.id == rule_id,
            PresetRegexRule.preset_id == preset_id
        )
    )
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()
    return rule
