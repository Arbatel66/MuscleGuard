from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db.database import create_db_and_tables
from llm.langGraph.lg_agent import LGFitnessAgent
from services.sync_service import HeartRateSyncService
from models import User

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（服务开始）
    load_dotenv()
    app.state.hr_sync = HeartRateSyncService()
    app.state.fit_agent = LGFitnessAgent()
    await create_db_and_tables()
    print("数据库表已检查/创建完成")

    # 创建checkpointer
    DB_URL = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    async with AsyncPostgresSaver.from_conn_string(DB_URL) as checkpointer:
        print("📌 checkpointer 连接成功")  # ← 加这行
        await checkpointer.setup()  # 首次运行自动建 checkpoint 相关表，之后幂等
        # 构建图
    print("📌 checkpointer setup 完成")  # ← 加这行

    try:
        yield
    finally:
        # 关闭时执行（服务停止）
        app.state.hr_sync.can_run.clear()
       

