from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB

class MemorySummary(SQLModel, table=True):
    __tablename__ = "memory_summary"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)     # 用户维度
    thread_id: str = Field(index=True)      # chat_xxx / plan_id
    scope: str = Field(index=True)          # "chat" / "training"
    source_message_count: int               # 这次总结基于多少条消息
    summary_text: str                       # 纯文本版，方便向量化
    summary_json: dict = Field(sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.now, index=True)