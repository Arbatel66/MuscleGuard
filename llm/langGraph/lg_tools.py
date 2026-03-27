import json

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel


@tool
def calculate_1rm(weight: float, reps: int) -> float:
    """Epley 公式：1RM = weight * (1 + reps / 30)"""
    return round(weight * (1 + reps / 30), 1)

# ── Tool 2: 查询历史训练数据（需要注入 db session，用工厂函数） ────────────
class GetExerciseHistoryInput(BaseModel):
    exercise_id: int


def make_exercise_history_tool(db_session):
    """
    工厂函数：把 db_session 注入进工具闭包。
    每次处理请求时调用一次，生成带有当前 db session 的工具。
    """

    async def _get_exercise_history(exercise_id: int) -> str:
        """查询用户该动作的历史训练数据，包括本组、近期组和历史组的重量/次数/心率。"""
        from services.fatigue_service import FatigueAnalyzer
        result = await FatigueAnalyzer.analysis_performance(db_session, exercise_id)
        return json.dumps(result, ensure_ascii=False, default=str)
    return StructuredTool.from_function(
        coroutine=_get_exercise_history,
        name="get_exercise_history",
        description="当历史记录不足以给出合理建议时调用该函数，查询用户该动作的历史训练数据，包括本组、近期和历史的重量/次数/心率数据。需要传入exercise_id。",
        args_schema=GetExerciseHistoryInput,
    )