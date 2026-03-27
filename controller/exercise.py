from fastapi import APIRouter, Request, Depends, HTTPException

from schemas.Workout_schemas import WorkoutPlanOut, WorkoutPlanCreate, PlanExerciseCreate, PlanExerciseOut, \
    ExerciseSetCreate, ExerciseSetOut
from services.exercise_service import ExerciseService
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_session
from services.fatigue_service import FatigueAnalyzer
from services.plan_service import PlanService
from services.sets_service import SetsService

router = APIRouter(prefix="/exercise", tags=["exercise"])

# response_model是后端返回给前端的类型
@router.get("/muscles_list" ,response_model=list[str])
async def muscles_list(db: AsyncSession = Depends(get_session)):
    # 使用 PostgreSQL 的 jsonb_array_elements 将数组展开并去重
    try:
        muscles = await ExerciseService.get_all_unique_muscles(db)
        return muscles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部位失败: {str(e)}")


@router.get("/exercise_list", response_model=list)
async def exercise_list(muscle:str, db: AsyncSession = Depends(get_session) ):
    # 使用 PostgreSQL 的 jsonb_array_elements 将数组展开并去重
    try:
        muscles = await ExerciseService.get_exercises_by_muscle(db, muscle)
        return muscles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取部位失败: {str(e)}")


@router.post("/create_plan", response_model=WorkoutPlanOut)
async def start_plan(plan_in: WorkoutPlanCreate, db: AsyncSession = Depends(get_session)):
    """
    创建一个训练计划
    :param plan_in:
    :param db:
    :return:
    """
    new_plan = await PlanService.create_plan(db, plan_in)

    return WorkoutPlanOut(
        plan_name = new_plan.plan_name,
        plan_id = new_plan.id,
        session_id = new_plan.session_id,
        start_time = new_plan.created_at
    )

@router.post("/add_exercises", response_model=PlanExerciseOut)
async def add_exercises(exercise_in: PlanExerciseCreate, db: AsyncSession = Depends(get_session)):
    """
    创建一个训练动作
    :param exercise_in:
    :param db:
    :return:
    """
    # 1. 存入数据库
    new_exercise = await ExerciseService.create_exercise(db, exercise_in)

    return PlanExerciseOut(
        plan_id =  new_exercise.plan_id,
        exercise_id = new_exercise.id,
        exercise_base_id = new_exercise.exercise_base_id,

    )

@router.post("/add_sets", response_model=ExerciseSetOut)
async def add_set(set_in: ExerciseSetCreate,
                  request: Request,
                  db: AsyncSession = Depends(get_session)
                  ):
    """
    创建一个训练组
    :param set_in:
    :param db:
    :param request:
    :return:
    """

    new_set = await SetsService.create_set(db, set_in)

    return ExerciseSetOut(
        set_id = new_set.id,
        exercise_id=new_set.exercise_id,
        weight=new_set.weight,
        reps=new_set.reps,
        peak_hr=new_set.peak_hr,
        rest_hr=new_set.rest_hr,
        score=new_set.score
    )