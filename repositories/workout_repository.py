# repositories/workout_repository.py
from sqlmodel import select
from models.Plan_Exercise_Model import ExerciseSet, PlanExercise, WorkoutPlan, BaseExercise


class WorkoutRepository:
    @staticmethod
    def get_sets_base_stmt():
        """
        查询set情况
        四表联查骨架：
        将 ExerciseSet -> PlanExercise -> WorkoutPlan ->BaseExercise串联

        """
        return (
            select(ExerciseSet)
            .join(PlanExercise, ExerciseSet.exercise_id == PlanExercise.id)
            .join(WorkoutPlan, PlanExercise.plan_id == WorkoutPlan.id)
            .join(BaseExercise, PlanExercise.exercise_base_id == BaseExercise.id)
        )

