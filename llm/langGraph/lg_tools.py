import json

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig
from llm.rag.rag_retriever import search_exercise_knowledge, search_summaries
from services.fatigue_service import FatigueAnalyzer
from services.plan_service import PlanService
from services.sets_service import SetsService
from datetime import datetime


@tool
def calculate_1rm(weight: float, reps: int) -> float:
    """Epley 公式：1RM = weight * (1 + reps / 30)"""
    return round(weight * (1 + reps / 30), 1)


@tool
async def get_exercise_history(exercise_id: int, config: RunnableConfig) -> str:
    """根据exercise_id查询该动作的所有历史记录。"""
    # 从 config 的 configurable 中提取你预先塞进去的 db_session
    db_session = config["configurable"].get("db_session")
    if db_session is None:
        return "错误：未获取到数据库连接，无法查询历史记录。"

    result = await FatigueAnalyzer.analysis_performance(db_session, exercise_id)
    if not result:
        return "未找到该动作的历史训练记录，请提示用户开始第一次训练。"
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
async def get_plan_history(limit: int = 5, config: RunnableConfig = None) -> str:
    """查询该用户的历史训练计划列表，limit默认为5条，传入更大的值可获取更多计划。返回包含 plan_id 和计划名称，可供后续用 get_sets_detail_by_plan_id 查询详情。"""
    # 从 config 的 configurable 中提取你预先塞进去的 db_session
    db_session = config["configurable"].get("db_session")
    if db_session is None:
        return "错误：未获取到数据库连接，无法查询历史记录。"

    session_id = config["configurable"].get("session_id")
    if session_id is None:
        return "错误：未获取到用户信息，无法查询历史记录。"

    result = await PlanService.get_plans_by_user_id(db_session, session_id, limit)
    if not result:
        return "未找到该用户历史训练计划，请提示用户开始第一次计划。"
    clean_result = [
        {
            "plan_id": r.id,
            "计划名称": r.plan_name,
            "日期": r.created_at,
        } for r in result
    ]
    return json.dumps(clean_result, ensure_ascii=False, default=str)

@tool
async def get_sets_detail_by_plan_id(plan_id: int, config: RunnableConfig) -> str:
    """根据plan_id查询该计划的所有动作及组数详情，返回包含动作名称、重量、次数、心率、评分等信息。"""
    db_session = config["configurable"].get("db_session")
    if db_session is None:
        return "错误：未获取到数据库连接，无法查询历史记录。"

    result = await SetsService.get_sets_with_names_by_plan_id(db_session, plan_id)
    if not result:
        return "未找到该计划的训练数据，请确认 plan_id 是否正确。"

    return json.dumps(result, ensure_ascii=False, default=str)

@tool
def get_current_time() -> str:
    """获取当前系统的日期和时间。当用户询问时间、日期或者需要根据时间做训练计划时，调用此工具。
    例子:例如出现'今天'，'上周'等关键词时
    """
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S 星期%w")