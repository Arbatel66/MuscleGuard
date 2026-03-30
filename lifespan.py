from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from db.database import create_db_and_tables
from llm.langGraph.lg_agent import LGFitnessAgent
from services.sync_service import HeartRateSyncService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行（服务开始）
    load_dotenv()
    app.state.hr_sync = HeartRateSyncService()
    app.state.fit_agent = LGFitnessAgent()
    await create_db_and_tables()
    print("数据库表已检查/创建完成")

    try:
        yield
    finally:
        # 关闭时执行（服务停止）
        app.state.hr_sync.can_run.clear()
       

