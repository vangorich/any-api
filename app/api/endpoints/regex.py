from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api import deps
from app.models.regex import RegexRule
from app.models.user import User
from app.schemas.regex import RegexRule as RegexRuleSchema, RegexRuleCreate, RegexRuleUpdate
from datetime import timezone

router = APIRouter()

@router.get("/", response_model=List[RegexRuleSchema])
async def read_regex_rules(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve regex rules.
    """
    query = select(RegexRule).filter(RegexRule.user_id == current_user.id).order_by(RegexRule.sort_order)
    result = await db.execute(query.offset(skip).limit(limit))
    rules = result.scalars().all()
    
    # 立即字符串化方案
    results = []
    for rule in rules:
        results.append({
            "id": rule.id,
            "name": rule.name,
            "pattern": rule.pattern,
            "replacement": rule.replacement,
            "type": rule.type,
            "is_active": rule.is_active,
            "sort_order": rule.sort_order,
            "user_id": rule.user_id,
            "creator_username": rule.creator_username,
            "created_at": rule.created_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
            "updated_at": rule.updated_at.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z'),
        })
    return results

@router.post("/", response_model=RegexRuleSchema)
async def create_regex_rule(
    *,
    db: AsyncSession = Depends(deps.get_db),
    rule_in: RegexRuleCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new regex rule.
    """
    rule = RegexRule(
        name=rule_in.name,
        pattern=rule_in.pattern,
        replacement=rule_in.replacement,
        type=rule_in.type,
        user_id=current_user.id,
        is_active=rule_in.is_active,
        sort_order=rule_in.sort_order,
        creator_username=current_user.username,  # 自动设置创建者用户名
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/{rule_id}", response_model=RegexRuleSchema)
async def update_regex_rule(
    *,
    db: AsyncSession = Depends(deps.get_db),
    rule_id: int,
    rule_in: RegexRuleUpdate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update regex rule.
    """
    result = await db.execute(select(RegexRule).filter(RegexRule.id == rule_id, RegexRule.user_id == current_user.id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.name = rule_in.name
    rule.pattern = rule_in.pattern
    rule.replacement = rule_in.replacement
    rule.type = rule_in.type
    rule.is_active = rule_in.is_active
    rule.sort_order = rule_in.sort_order
    
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/{rule_id}", response_model=RegexRuleSchema)
async def delete_regex_rule(
    *,
    db: AsyncSession = Depends(deps.get_db),
    rule_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete regex rule.
    """
    result = await db.execute(select(RegexRule).filter(RegexRule.id == rule_id, RegexRule.user_id == current_user.id))
    rule = result.scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()
    return rule
