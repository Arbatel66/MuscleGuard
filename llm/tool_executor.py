# tool_executor.py 里的工具实现
import json
from sqlalchemy.ext.asyncio import AsyncSession

from services.fatigue_service import FatigueAnalyzer
from services.sets_service import SetsService

def calculate_1rm(weight: float, reps: int) -> float:
    """Epley 公式：1RM = weight * (1 + reps / 30)"""
    return round(weight * (1 + reps / 30), 1)

async def get_recent_sets_stats(exercise_id: int,
                                   session: AsyncSession) -> str:
    # 1. Service 层查数据（有IO）

    all_recent_sets = await SetsService.get_sets_by_exercise_id(session, exercise_id)
    current_set = all_recent_sets[0]  # 这是【当前组】
    history_sets = await SetsService.get_history_set_by_exercise_id(session, exercise_id, limit=10)

    # 2. FatigueAnalyzer 纯计算（无IO）
    history_score = FatigueAnalyzer._compute_recovery_60s_score()
    history_score += FatigueAnalyzer.compute_history_exercise_peak_score(current_set, history_sets)

    return json.dumps({"history_fatigue_extra_score": history_score, "history_count": len(history_sets)})

async def execute_tool(tool_name: str, arguments: dict) -> str:
    """
    根据 tool_name 执行对应函数，返回 JSON 字符串结果。
    LLM 需要的是字符串格式的结果。
    """
    if tool_name == "calculate_1rm":
        weight = arguments["weight"]
        reps = arguments["reps"]
        one_rm = calculate_1rm(weight, reps)
        return json.dumps({
            "estimated_1rm_kg": one_rm,
            "formula": "Epley: weight * (1 + reps/30)"
        }, ensure_ascii=False)
    return json.dumps({"error": f"未知工具: {tool_name}"})


