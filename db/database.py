import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

load_dotenv()

# 核心变化 1: 协议头必须改为 postgresql+asyncpg
# 原来是: postgresql://...
# 现改为: postgresql+asyncpg://...
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")

# 核心变化 2: 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# 核心变化 3: 创建异步会话生成器
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def create_db_and_tables():
    """异步初始化表结构"""
    async with engine.begin() as conn:
        # 这一步目前仍需在同步环境下扫描模型，但可以使用 conn.run_sync
        # create_all会扫描所有的SQLModel(table=True)并创建表
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session():
    """异步 Dependency Injection"""
    async with async_session_factory() as session:
        yield session