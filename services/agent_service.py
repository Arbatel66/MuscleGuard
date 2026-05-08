from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from sqlmodel import select

from models.MemorySummary_Model import MemorySummary
from models.Plan_Exercise_Model import PlanExercise, BaseExercise
from schemas.Workout_schemas import PlanExerciseCreate


class AgentService:

    @staticmethod
    def summary_json_to_text(payload: dict) -> str:
        parts = []

        if payload.get("title"):
            parts.append(f"标题：{payload['title']}")
        if payload.get("summary"):
            parts.append(f"摘要：{payload['summary']}")

        mapping = [
            ("key_facts", "关键信息"),
            ("injuries", "伤痛/不适"),
            ("preferences", "偏好"),
            ("goals", "目标"),
            ("risks", "风险"),
            ("next_focus", "后续关注"),
        ]

        for key, label in mapping:
            values = payload.get(key) or []
            if values:
                parts.append(f"{label}：" + "；".join(values))

        return "\n".join(parts)

    @staticmethod
    async def save_summary_to_db(
            db: AsyncSession,
            *,
            session_id: str,
            thread_id: str,
            scope: str,
            source_message_count: int,
            summary_payload: dict,
    ) -> MemorySummary:

        summary_text = AgentService.summary_json_to_text(summary_payload)

        record = MemorySummary(
            session_id=session_id,
            thread_id=thread_id,
            scope=scope,
            source_message_count=source_message_count,
            summary_text=summary_text,
            summary_json=summary_payload,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def get_latest_summaries(
            session: AsyncSession,
            session_id: str,
            limit: int = 3,
            scope: Optional[str] = None
    ) -> List[MemorySummary]:
        """
        获取指定用户最近的 n 条总结

        Args:
            session: 数据库会话
            session_id: 用户 ID
            limit: 返回数量
            scope: 可选，过滤 scope（"chat" 或 "training"）
        """
        statement = (
            select(MemorySummary)
            .where(MemorySummary.session_id == session_id)
        )
        if scope:
            statement = statement.where(MemorySummary.scope == scope)

        statement = statement.order_by(MemorySummary.created_at.desc()).limit(limit)

        result = await session.execute(statement)
        summaries = list(result.scalars().all())
        return summaries