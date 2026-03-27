from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from models.Plan_Exercise_Model import WorkoutPlan
from schemas.Workout_schemas import WorkoutPlanCreate
from sqlmodel import select
from models.Plan_Exercise_Model import BaseExercise
from sqlalchemy import or_

class PlanService:
    @staticmethod
    async def create_plan(session: AsyncSession, plan_in: WorkoutPlanCreate) -> WorkoutPlan:
        """
        创建计划
        id: Optional[int] = Field(default=None, primary_key=True)
        session_id: str = Field(index=True)  # 你的唯一用户标识
        plan_name: str
        created_at: datetime = Field(default_factory=datetime.now)
        """
        # id 和 created_at 会由 SQLModel 的 Field 定义自动处理
        new_plan = WorkoutPlan(
            session_id=plan_in.session_id,
            plan_name=plan_in.plan_name
        )
        session.add(new_plan)
        await session.commit()
        # 3. 刷新以获取数据库生成的 id 和 默认的 created_at
        await session.refresh(new_plan)
        return new_plan

    @staticmethod
    async def get_plan_by_id(session: AsyncSession, plan_id: int) -> Optional[WorkoutPlan]:
        return await session.get(WorkoutPlan, plan_id)

