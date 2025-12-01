from fastapi import FastAPI
from contextlib import asynccontextmanager
import os
from app.core.config import settings
from app.core.database import engine, Base
from app.models.system_config import SystemConfig
from app.core.database import get_db
from sqlalchemy import select
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directory exists
    if "sqlite" in settings.DATABASE_URL:
        db_path = settings.DATABASE_URL.split("///")[1]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    # Startup: Load site name from DB and set as app title
    db_session_gen = get_db()
    db = await anext(db_session_gen)
    try:
        stmt = select(SystemConfig)
        config = (await db.execute(stmt)).scalars().first()
        if config and config.site_name:
            app.title = config.site_name
        else:
            app.title = "Any API"
    except Exception as e:
        print(f"警告: 无法加载系统配置: {e}")
        print("提示: 如果这是首次运行,请执行: python migrate.py upgrade")
    finally:
        await db.close()
            
    yield

app = FastAPI(
    title="Any API",
    version=settings.VERSION,
    openapi_url=f"{settings.VITE_API_STR}/openapi.json",
    lifespan=lifespan
)

# 注册全局异常处理器
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.core.exception_handlers import (
    api_exception_handler, 
    validation_exception_handler, 
    general_exception_handler
)
app.add_exception_handler(HTTPException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# --- 路由注册 ---

# 1. API 路由 (按照从最精确到最宽泛的顺序)
from app.api.api import api_router
from app.api.endpoints import generic_proxy, proxy, gemini_routes, claude_routes, universal_routes

app.include_router(api_router, prefix=settings.VITE_API_STR)

# 2. 静态文件服务 (必须在API路由之后,但在通配符路由之前)
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 3. 其他API路由
app.include_router(gemini_routes.router)
app.include_router(proxy.router)
app.include_router(claude_routes.router)
# app.include_router(universal_routes.router)
# app.include_router(generic_proxy.router, tags=["generic_proxy"])

# 4. SPA 前端 "后备" 路由 (必须在最后)
# 4. SPA 前端服务 (必须在最后)
static_dir = "static" if os.path.exists("static") else "dist"
if os.path.exists(static_dir):
    # 1. 挂载静态文件目录,处理所有静态资源请求 (CSS, JS, images, etc.)
    app.mount("/", StaticFiles(directory=static_dir), name="static_assets")

    # 2. 创建一个后备路由,捕获所有未被API或静态文件处理的路径
    #    这确保了在使用前端路由(如/dashboard/system)时刷新页面能正确加载应用
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(static_dir, "index.html"))
else:
    print("警告: 静态文件目录 'static' 或 'dist' 未找到,前端将无法访问。")
    @app.get("/", include_in_schema=False)
    async def root_api_only():
        return {"message": "Welcome to Any API (Frontend not found)"}

# 这个启动块仅用于 python app/main.py 直接运行, uvicorn CLI 不会执行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
