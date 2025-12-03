import httpx
import logging
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.key import OfficialKey
from app.models.system_config import SystemConfig
from app.core.config import settings

# 获取一个名为 __name__ (当前模块名) 的 logger 实例
logger = logging.getLogger(__name__)

# --- 日志基础配置 ---
# 检查 logger 是否已经有处理器，防止重复添加
if not logger.handlers:
    # 创建一个流处理器，将日志输出到控制台
    handler = logging.StreamHandler()
    # 定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # 为处理器设置格式
    handler.setFormatter(formatter)
    # 为 logger 添加处理器
    logger.addHandler(handler)
    # 设置 logger 的默认级别为 INFO
    logger.setLevel(logging.INFO)

class GeminiService:
    def __init__(self):
        # --- API 限制要素 1: 客户端连接限制 ---
        # 设置 httpx 客户端的连接限制
        # max_keepalive_connections: 最大保持的长连接数，用于连接复用，提高效率
        # max_connections: 最大并发连接总数。这是一个重要的客户端侧限流措施，防止对目标API造成过大压力。
        limits = httpx.Limits(max_keepalive_connections=100, max_connections=1000)
        
        # --- API 限制要素 2: 请求超时 ---
        # 设置请求超时时间。总超时60秒，连接超时10秒。
        # 防止请求因网络问题长时间卡死，保证服务的响应性。
        timeout = httpx.Timeout(60.0, connect=10.0)
        
        # 初始化异步 httpx 客户端，用于后续向 Gemini API 发送请求
        self.client = httpx.AsyncClient(
            base_url=settings.GEMINI_BASE_URL, # API 的基础 URL
            timeout=timeout,                   # 应用超时配置
            limits=limits,                     # 应用连接限制配置
            follow_redirects=True              # 自动处理 HTTP 重定向
        )

    def update_log_level(self, level_name: str):
        """动态更新日志级别"""
        # getattr 用于从 logging 模块动态获取日志级别常量，如 logging.INFO
        level = getattr(logging, level_name.upper(), logging.INFO)
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)

    async def close(self):
        """优雅地关闭 httpx 客户端，释放资源"""
        await self.client.aclose()

    async def get_next_key(self, db: AsyncSession, channel_id: int = None) -> OfficialKey:
        """
        --- API 限制要素 3: 密钥轮询调度 (Round-Robin) ---
        使用轮询策略获取数据库中的下一个官方密钥，此方法不检查密钥的激活状态。
        这是实现负载均衡、规避单一密钥速率限制的核心逻辑。
        """
        # 创建一个查询，选择所有的 OfficialKey
        stmt = select(OfficialKey)
        # 如果指定了渠道ID，则只在该渠道内筛选密钥
        if channel_id:
            stmt = stmt.filter(OfficialKey.channel_id == channel_id)
        
        # 按 ID 排序，以确保每次轮询的顺序是固定的
        stmt = stmt.order_by(OfficialKey.id)
        result = await db.execute(stmt)
        # 获取所有符合条件的密钥对象列表
        keys = result.scalars().all()

        # 如果数据库中没有任何密钥，则抛出异常
        if not keys:
            raise HTTPException(status_code=503, detail=f"No official keys configured{' for this channel' if channel_id else ''}")

        # 从数据库中获取系统配置，主要为了读取上一次使用的密钥ID
        config_result = await db.execute(select(SystemConfig))
        config = config_result.scalars().first()
        # 如果配置不存在，则创建一个新的
        if not config:
            config = SystemConfig()
            db.add(config)
        
        last_key_id = config.last_used_official_key_id
        next_key = None

        # --- 轮询逻辑实现 ---
        if last_key_id:
            try:
                # 找到上一次使用的 key 在当前列表中的索引
                last_key_index = next(i for i, key in enumerate(keys) if key.id == last_key_id)
                # 计算下一个 key 的索引，使用取模运算实现循环
                next_key_index = (last_key_index + 1) % len(keys)
                next_key = keys[next_key_index]
            except StopIteration:
                # 如果上一次使用的 key 不在当前列表中（比如被删了），则从第一个开始
                next_key = keys[0]
        else:
            # 如果是第一次使用，也从第一个 key 开始
            next_key = keys[0]

        # 更新系统配置，记下本次使用的密钥ID，为下一次轮询做准备
        config.last_used_official_key_id = next_key.id
        await db.commit()
        return next_key

    async def get_active_key(self, db: AsyncSession, channel_id: int = None) -> OfficialKey:
        """
        查找并返回一个处于“激活”状态的 OfficialKey。
        这个方法结合了密钥轮询和状态检查。
        """
        # 查询所有密钥，用于确定轮询的最大次数
        stmt = select(OfficialKey)
        if channel_id:
            stmt = stmt.filter(OfficialKey.channel_id == channel_id)
        
        result = await db.execute(stmt)
        all_keys = result.scalars().all()
        
        if not all_keys:
            raise HTTPException(status_code=503, detail=f"No official keys configured{' for this channel' if channel_id else ''}")
        
        # 尝试最多遍历一遍所有密钥，来寻找一个可用的
        # 这是一个保护措施，防止在所有key都失效时陷入无限循环
        for _ in range(len(all_keys)):
            key_obj = await self.get_next_key(db, channel_id=channel_id)
            # 检查获取到的密钥是否是激活状态
            if key_obj.is_active:
                # 如果是，则直接返回
                return key_obj

        # 如果遍历了一整圈还是没找到可用的密钥，说明所有密钥都失效了
        raise HTTPException(status_code=503, detail=f"All official keys are disabled{' for this channel' if channel_id else ''}")

    async def get_active_key_str(self, db: AsyncSession, channel_id: int = None) -> str:
        """
        一个便捷方法，直接查找并返回一个激活状态的密钥字符串。
        """
        key_obj = await self.get_active_key(db, channel_id=channel_id)
        return key_obj.key

    async def update_key_status(self, db: AsyncSession, key_str: str, status_code: int, input_tokens: int = 0, output_tokens: int = 0):
        """
        --- API 限制要素 4: 自动熔断机制 (Circuit Breaker) ---
        根据API调用的返回状态码来更新密钥的状态。
        这是实现自动禁用失效密钥（熔断）的关键。
        """
        # 根据密钥字符串查找对应的密钥对象
        result = await db.execute(select(OfficialKey).filter(OfficialKey.key == key_str))
        key = result.scalars().first()
        if key:
            key.last_status_code = status_code # 记录最后一次的状态码
            key.usage_count += 1               # 使用次数加1

            # 如果状态码表示成功 (2xx)
            if 200 <= status_code < 300:
                key.total_tokens = (key.total_tokens or 0) + input_tokens + output_tokens
                key.error_count = 0  # 成功后，重置连续错误计数
                key.last_status = str(status_code)
            else:
                # 如果API调用失败
                key.error_count = (key.error_count or 0) + 1
                
                # --- 熔断逻辑 ---
                # 如果连续错误次数达到或超过3次
                if key.error_count >= 3:
                    key.is_active = False # 将密钥状态设置为不活跃，自动禁用
                    key.last_status = "auto_disabled" # 记录为自动禁用状态
                else:
                    key.last_status = str(status_code)

            await db.commit()

# 创建 GeminiService 的单例，供整个应用使用
gemini_service = GeminiService()
