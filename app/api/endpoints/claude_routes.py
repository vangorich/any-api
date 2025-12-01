from typing import AsyncGenerator
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, Response, JSONResponse
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.claude_service import claude_service
from app.api import deps
from app.core.database import get_db
from app.services.proxy_service import proxy_service

router = APIRouter()

@router.api_route("/v1/messages", methods=["POST"])
async def proxy_claude_messages(
    request: Request,
    key_info: tuple = Depends(deps.get_official_key_from_proxy),
    db: AsyncSession = Depends(get_db)
):
    """
    Proxy for Claude Messages API (/v1/messages).
    Transmits key and body directly to Anthropic.
    """
    official_key, user = key_info
    
    # 使用 ProxyService 处理
    return await proxy_service.smart_proxy_handler(
        request=request,
        path="messages",
        official_key=official_key,
        incoming_format="claude"
    )

@router.api_route("/v1/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_claude_generic(
    path: str,
    request: Request,
    key_info: tuple = Depends(deps.get_official_key_from_proxy),
    db: AsyncSession = Depends(get_db)
):
    """
    Generic Proxy for other Claude endpoints (e.g. /v1/complete for legacy).
    """
    official_key, user = key_info
    
    excluded_headers = {"host", "content-length", "authorization"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}
    headers["x-api-key"] = official_key
    headers["anthropic-version"] = headers.get("anthropic-version", "2023-06-01")

    body = await request.body()
    
    # 使用 ProxyService 智能处理通用 /v1 请求
    # 这样即使用户访问的是非 messages 接口，甚至是非 Claude 接口（如果路由落到这里），
    # 也能根据 Key 尝试正确转发
    return await proxy_service.smart_proxy_handler(
        request=request,
        path=path,
        official_key=official_key,
        incoming_format="claude" # 假设落在 Claude 路由上的请求默认为 Claude 格式
    )