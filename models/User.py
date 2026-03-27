# models.py
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """
    table=True 告诉 SQLModel 这是一个数据库表模型
    """
    # session_id 是第三方 App 提供的唯一标识，我们把它设为主键
    session_id: str = Field(primary_key=True, index=True)
    name: str
    age: int
    height: float  # 身高 (cm)
    weight: float  # 体重 (kg)

    # 你甚至可以预留一个字段存用户的目标，比如“增肌”或“减脂”