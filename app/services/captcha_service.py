import random
import string
import uuid
from io import BytesIO
from captcha.image import ImageCaptcha
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import base64
from app.models.captcha import Captcha

class CaptchaService:
    def __init__(self):
        self.image_captcha = ImageCaptcha(width=150, height=50)

    def generate_code(self, length=4):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    async def create_captcha(self, db: AsyncSession):
        captcha_id = str(uuid.uuid4())
        code = self.generate_code()
        
        new_captcha = Captcha(id=captcha_id, code=code)
        db.add(new_captcha)
        await db.commit()
        
        image_data = self.image_captcha.generate(code)
        return captcha_id, image_data

    async def generate_captcha(self, db: AsyncSession) -> tuple[str, str]:
        """
        生成验证码并返回ID和Base64编码的图片
        """
        captcha_id, image_data = await self.create_captcha(db)
        # 将图片数据转换为Base64
        image_b64 = base64.b64encode(image_data.read()).decode('utf-8')
        return captcha_id, image_b64

    async def verify_captcha(self, db: AsyncSession, captcha_id: str, user_code: str) -> bool:
        if not captcha_id or not user_code:
            return False
            
        result = await db.execute(select(Captcha).filter(Captcha.id == captcha_id))
        captcha = result.scalars().first()
        
        if not captcha:
            return False
        
        # 验证成功后不立即删除，以便后续的send-code请求能再次验证
        # 验证失败或过期则删除
        is_correct = captcha.code.lower() == user_code.lower()
        
        if not is_correct or captcha.is_expired():
            await db.delete(captcha)
            await db.commit()
            return False
            
        # 如果验证正确，暂时不删除
        return True

captcha_service = CaptchaService()