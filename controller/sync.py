from dataclasses import dataclass
from fastapi import APIRouter, Request, Depends, HTTPException
import asyncio
import time
from schemas.Workout_schemas import ExerciseSetCreate
from services.exercise_service import ExerciseService
from services.fatigue_service import FatigueAnalyzer
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_session
from services.sets_service import SetsService

router = APIRouter(prefix="/sync", tags=["sync"])


@dataclass
class _TempSet:
    weight: float
    reps: int
    peak_hr: int


@router.post("/create_polling")
async def create_polling(request: Request, session_id: str):
    svc = request.app.state.hr_sync
    user_hr_sync = svc.get_or_create(session_id)

    asyncio.create_task(user_hr_sync.create_polling(session_id))


@router.post("/pause_polling")
async def pause_polling(
        request: Request,
        session_id: str,
        set_in: ExerciseSetCreate,
        db: AsyncSession = Depends(get_session)
):
    """
    用户完成一组后调用：
    - set_in (body): exercise_id, weight, reps
    - peak_hr / rest_hr 从心率服务自动获取
    - 计算疲劳评分后创建 ExerciseSet 记录
    """
    svc = request.app.state.hr_sync
    user_hr_sync = svc.get_or_create(session_id)
    user_hr_sync.pause_polling()

    # 1. 从心率服务拿生理数据
    fa = FatigueAnalyzer(user_hr_sync)
    rest_hr = fa.metrics.last_hr
    peak_hr = fa.metrics.peak_bpm
    exercise_id = set_in.exercise_id

    # 2. 查历史数据用于历史对比评分
    history_sets = await SetsService.get_history_set_by_exercise_id(db, exercise_id)

    # 3. 构建临时当前组对象（纯计算用）
    current_set = _TempSet(weight=set_in.weight, reps=set_in.reps, peak_hr=peak_hr)

    # 4. 计算疲劳评分，填入 set_in
    set_in.rest_hr = rest_hr
    set_in.peak_hr = peak_hr
    score = fa.run_full_analysis(current_set, history_sets)
    set_in.score = score
    print(f"last_hr:{rest_hr}  peak_bpm:{peak_hr}  score:{score}")

    # 5. 存入数据库
    new_set = await SetsService.create_set(db, set_in)

    # 获取plan_id当作lg_agent checkoutpointer的thread_id
    plan_id = await ExerciseService.get_plan_id_by_exercise_id(db,exercise_id)
    if plan_id is None:
        raise HTTPException(status_code=404, detail=f"exercise_id {exercise_id} 不存在")

    # 6. LLM Tool Calling 分析
    # llm = LLM_Client()
    # fit_agent = FitnessAgent(llm)
    fit_agent = request.app.state.fit_agent

    llm_analysis = await fit_agent.lg_run_analysis(
        db=db,
        session_id=session_id,
        fatigue_analyzer=fa,
        current_set=new_set,
        plan_id = plan_id
    )


    return {
        "set_id": new_set.id,
        "score": set_in.score,
        "peak_hr": peak_hr,
        "rest_hr": rest_hr,
        "analysis": llm_analysis,
        "status": "success"
    }


@router.post("/resume_polling")
async def resume_polling(request: Request, session_id:str):
    svc = request.app.state.hr_sync
    user_hr_sync = svc.get_or_create(session_id)
    user_hr_sync.resume_polling()


@router.get("/current_hr")
async def display_current_hr(request: Request, session_id:str):
    svc = request.app.state.hr_sync
    user_hr_sync = svc.get_or_create(session_id)
    return user_hr_sync.last_value

@router.post("/end_plan")
async def end_plan(request: Request, session_id: str, plan_id: int, db: AsyncSession = Depends(get_session)):
    # 1.生成一个今日训练总结
    # 2.返回给前端后执行训练模块的summary
    fit_agent = request.app.state.fit_agent
    summary = await fit_agent.lg_summarize_training(db=db, session_id=session_id, plan_id=plan_id)
    return {
        "message": "训练计划已完成",
        "summary": summary
    }


