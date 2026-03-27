from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException
from models.User import User

class UserService:
    # 静态方法没法访问“类本身”或“实例对象”内部的东西只能处理传入的参数
    @staticmethod
    async def create_new_user(db: AsyncSession, user_data: User) -> User:
        # 1. 业务逻辑：检查重复
        statement = select(User).where(User.session_id == user_data.session_id)
        result = await db.execute(statement)
        if result.first():
            raise HTTPException(status_code=400, detail="该 Session ID 已被注册")

        # 2. 执行写入
        db.add(user_data)
        try:
            await db.commit()
            await db.refresh(user_data)
            return user_data
        except Exception as e:
            await db.rollback()
            # 这里抛出的异常会被 Controller 捕获或直接透传
            raise e

    @staticmethod
    async def get_user_by_id(db: AsyncSession, session_id: str) -> User:
        """这是给别的文件调用的标准接口"""
        statement = select(User).where(User.session_id == session_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()  # 返回对象或 None

    @staticmethod
    async def generate_user_context (db: AsyncSession, session_id: str) -> Dict[str, Any]:
        """
        传入一个session_id返回该用户的结构化数据
        """
        statement = select(User).where(User.session_id == session_id)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        return {
            "user_context": {
                "user_name": user.name,
                "user_age": user.age,
                "user_weight_kg": user.weight,
                "user_height_cm": user.height,
            },
        }
