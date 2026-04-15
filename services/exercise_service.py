from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from sqlmodel import select

from models.Plan_Exercise_Model import PlanExercise, BaseExercise
from schemas.Workout_schemas import PlanExerciseCreate


class ExerciseService:
    @staticmethod
    async def get_all_unique_muscles(session: AsyncSession) -> List[str]:
        """
        从 base_exercise 表中提取所有去重后的主要和次要肌群
        """
        query = text("""
                SELECT DISTINCT muscle 
                FROM (
                    SELECT jsonb_array_elements_text(primary_muscles) as muscle FROM base_exercise
                    UNION
                    SELECT jsonb_array_elements_text(secondary_muscles) as muscle FROM base_exercise
                ) as combined_muscles
                WHERE muscle IS NOT NULL
                ORDER BY muscle;
            """)

        result = await session.execute(query)
        muscles = [row[0] for row in result]
        return muscles

    @staticmethod
    async def get_exercises_by_muscle(session: AsyncSession, muscle: str):
        """根据选定的部位获取动作列表"""
        from sqlalchemy import or_

        statement = select(BaseExercise).where(
            or_(
                BaseExercise.primary_muscles.contains([muscle]),
                BaseExercise.secondary_muscles.contains([muscle])
            )
        )
        result = await session.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def create_exercise(session: AsyncSession, exercise_in: PlanExerciseCreate) -> PlanExercise:
        new_exercise = PlanExercise(
            plan_id=exercise_in.plan_id,
            exercise_base_id=exercise_in.exercise_base_id
        )
        session.add(new_exercise)
        await session.commit()
        await session.refresh(new_exercise)
        return new_exercise

    @staticmethod
    async def get_exercise_by_id(session: AsyncSession, exercise_id: int) -> Optional[PlanExercise]:
        return await session.get(PlanExercise, exercise_id)

    @staticmethod
    async def get_plan_id_by_exercise_id(session: AsyncSession, exercise_id: int) -> int:
        statement = select(PlanExercise.plan_id).where(PlanExercise.id == exercise_id)
        result = await session.execute(statement)
        plan_id = result.scalar_one_or_none()
        return plan_id

    @staticmethod
    async def get_exercises_by_plan_id(session: AsyncSession, plan_id: int) -> List[tuple[PlanExercise, str]]:
        statement = (
            select(PlanExercise, BaseExercise.name)
            .join(BaseExercise, PlanExercise.exercise_base_id == BaseExercise.id)
            .where(PlanExercise.plan_id == plan_id)
        )

        result = await session.execute(statement)
        return [(plan_exercise, exercise_name) for plan_exercise, exercise_name in result.all()]
