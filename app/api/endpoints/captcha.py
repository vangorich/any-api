from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.verification_code import CaptchaVerifyRequest
from app.services.captcha_service import captcha_service

router = APIRouter()

@router.post("/verify", tags=["captcha"])
async def verify_captcha_endpoint(
    request: CaptchaVerifyRequest,
    db: AsyncSession = Depends(deps.get_db)
):
    """
    独立的图形验证码验证端点，用于弹窗等场景的预验证。
    """
    is_valid = await captcha_service.verify_captcha(db, request.captcha_id, request.captcha_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="验证码错误")
    return {"message": "验证成功"}

@router.get("/generate", tags=["captcha"])
async def generate_captcha(db: AsyncSession = Depends(deps.get_db)):
    """
    生成一个新的图形验证码。
    """
    captcha_id, image_b64 = await captcha_service.generate_captcha(db)
    return {"captcha_id": captcha_id, "image": image_b64}