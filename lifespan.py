from contextlib import asynccontextmanager
from fastapi import FastAPI

from db.database import create_db_and_tables
from services.sync_service import HeartRateSyncService
from models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（服务开始）
    app.state.hr_sync = HeartRateSyncService()
    await create_db_and_tables()
    print("数据库表已检查/创建完成")

    try:
        yield
    finally:
        # 关闭时执行（服务停止）
        app.state.hr_sync.can_run.clear()
       

