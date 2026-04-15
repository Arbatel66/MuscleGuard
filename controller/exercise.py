from fastapi import APIRouter, Request, Depends, HTTPException

from schemas.Workout_schemas import WorkoutPlanOut, WorkoutPlanCreate, PlanExerciseCreate, PlanExerciseOut, \
    ExerciseSetCreate, ExerciseSetOut, ShowPlansDetail, ShowSetsDetail, ShowExerciseDetail
from services.exercise_service import ExerciseService
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_session
from services.plan_service import PlanService
from services.sets_service import SetsService

router = APIRouter(prefix="/exercise", tags=["exercise"])


@router.get("/muscles_list", response_model=list[str])
async def muscles_list(db: AsyncSession = Depends(get_session)):
    try:
        muscles = await ExerciseService.get_all_unique_muscles(db)
        return muscles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部位失败: {str(e)}")


@router.get("/exercise_list", response_model=list)
async def exercise_list(muscle: str, db: AsyncSession = Depends(get_session)):
    try:
        muscles = await ExerciseService.get_exercises_by_muscle(db, muscle)
        return muscles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部位失败: {str(e)}")


@router.post("/create_plan", response_model=WorkoutPlanOut)
async def start_plan(plan_in: WorkoutPlanCreate, db: AsyncSession = Depends(get_session)):
    new_plan = await PlanService.create_plan(db, plan_in)

    return WorkoutPlanOut(
        plan_name=new_plan.plan_name,
        plan_id=new_plan.id,
        session_id=new_plan.session_id,
        start_time=new_plan.created_at
    )


@router.post("/add_exercises", response_model=PlanExerciseOut)
async def add_exercises(exercise_in: PlanExerciseCreate, db: AsyncSession = Depends(get_session)):
    new_exercise = await ExerciseService.create_exercise(db, exercise_in)

    return PlanExerciseOut(
        plan_id=new_exercise.plan_id,
        exercise_id=new_exercise.id,
        exercise_base_id=new_exercise.exercise_base_id,
    )


@router.post("/add_sets", response_model=ExerciseSetOut)
async def add_set(
    set_in: ExerciseSetCreate,
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    new_set = await SetsService.create_set(db, set_in)

    return ExerciseSetOut(
        set_id=new_set.id,
        exercise_id=new_set.exercise_id,
        weight=new_set.weight,
        reps=new_set.reps,
        peak_hr=new_set.peak_hr,
        rest_hr=new_set.rest_hr,
        score=new_set.score
    )


@router.get("/get_plans", response_model=list[ShowPlansDetail])
async def show_plans_detail(session_id: str, db: AsyncSession = Depends(get_session)):
    output_plans = []
    plans = await PlanService.get_plans_by_user_id(db, session_id)

    for p in plans:
        output_exercise = []
        exercises = await ExerciseService.get_exercises_by_plan_id(db, p.id)

        for e, exercise_name in exercises:
            sets = await SetsService.get_sets_by_exercise_id(db, e.id)
            output_sets = [
                ShowSetsDetail(
                    set_id=s.id,
                    weight=s.weight,
                    reps=s.reps,
                    peak_hr=s.peak_hr,
                    rest_hr=s.rest_hr,
                    score=s.score,
                )
                for s in sets
            ]

            output_exercise.append(
                ShowExerciseDetail(
                    plan_id=e.plan_id,
                    exercise_id=e.id,
                    exercise_base_id=e.exercise_base_id,
                    exercise_name=exercise_name,
                    sets=output_sets,
                )
            )

        output_plans.append(
            ShowPlansDetail(
                plan_name=p.plan_name,
                plan_id=p.id,
                session_id=session_id,
                start_time=p.created_at,
                exercises=output_exercise,
            )
        )

    return output_plans
