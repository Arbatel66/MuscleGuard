from sqlalchemy import text, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from sqlmodel import select

from models.Plan_Exercise_Model import ExerciseSet, WorkoutPlan, BaseExercise, PlanExercise
from repositories.workout_repository import WorkoutRepository
from schemas.Workout_schemas import  ExerciseSetCreate
from services.exercise_service import ExerciseService
from services.plan_service import PlanService


class SetsService:
    @staticmethod
    async def create_set(session: AsyncSession, set_in: ExerciseSetCreate) -> ExerciseSet:
        """
        创建set
        :arg
            id: Optional[int] = Field(default=None, primary_key=True)

            exercise_id: int = Field(foreign_key="planexercise.id")
            weight: float
            reps: int
            peak_hr: int
            rest_hr: int
            score : int

        """
        # id 和 created_at 会由 SQLModel 的 Field 定义自动处理
        new_set = ExerciseSet(
            exercise_id=set_in.exercise_id,
            weight = set_in.weight,
            reps = set_in.reps,
            peak_hr = set_in.peak_hr,
            rest_hr = set_in.rest_hr,
            score = set_in.score
        )
        session.add(new_set)
        await session.commit()
        # 3. 刷新以获取数据库生成的 id 和 默认的 created_at
        await session.refresh(new_set)
        return new_set

    @staticmethod
    async def get_set_by_id(session: AsyncSession, set_id: int) -> ExerciseSet:

        statement = select(ExerciseSet).where( ExerciseSet.id ==set_id )
        result = await session.execute(statement)
        return result.scalars().first()

    @staticmethod
    async def get_sets_by_exercise_id(session: AsyncSession, exercise_id: int, limit: int = None) -> List[ExerciseSet]:

        statement = (select(ExerciseSet)
                     .where( ExerciseSet.exercise_id == exercise_id )
                        .order_by(desc(ExerciseSet.id))
                     )
        if limit:
            statement = statement.limit(limit)
        result = await session.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def get_history_set_by_exercise_id(
            session: AsyncSession, exercise_id: int, limit: int = None
    ) -> List[ExerciseSet]:
        # 一次查询拿到 session_id + exercise_base_id
        stmt = (
            select(WorkoutPlan.session_id, PlanExercise.exercise_base_id)
            .join(WorkoutPlan, PlanExercise.plan_id == WorkoutPlan.id)
            .where(PlanExercise.id == exercise_id)
        )
        result = await session.execute(stmt)
        row = result.first()
        if not row:
            return []
        session_id, exercise_base_id = row

        # 四表联查历史
        statement = (
            WorkoutRepository.get_sets_base_stmt()
            .where(WorkoutPlan.session_id == session_id)
            .where(PlanExercise.exercise_base_id == exercise_base_id)
            .order_by(desc(ExerciseSet.id))
        )
        # 跳过排序后的第一条
        statement = statement.offset(1)
        if limit:
            statement = statement.limit(limit)
        result = await session.execute(statement)
        return list(result.scalars().all())
