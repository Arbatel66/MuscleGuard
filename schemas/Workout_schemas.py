
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

#训练计划，包含多个动作
class WorkoutPlanCreate(BaseModel):
    plan_name: str          # 比如 "周一胸部训练" 或 "今日随机练"
    session_id: str            # 当前登录用户的 ID
    # start_time 通常由后端自动生成，所以这里可以不传，或者可选

class WorkoutPlanOut(BaseModel):
    plan_name: str          # 比如 "周一胸部训练" 或 "今日随机练"
    plan_id: int            # 创建plan后生成的plan.id回传给前端
    session_id: str            # 当前登录用户的 ID
    # 建议加上开始时间，前端可能需要显示
    start_time: datetime

    # 允许从 SQLModel 对象直接读取数据
    model_config = ConfigDict(from_attributes=True)


#训练动作 ：如卧推 包含多个组
class PlanExerciseCreate(BaseModel):
    plan_id: int            # 第一步生成的 WorkoutPlan 的 ID
    exercise_base_id: str   # 标准库里的动作 ID，例如 "Barbell_Bench_Press

class PlanExerciseOut(BaseModel):
    plan_id: int            # 第一步生成的 WorkoutPlan 的 ID
    exercise_id: int        # 创建exercise后生成的exercise.id回传给前端
    exercise_base_id: str  # 标准库里的动作 ID，例如 "Barbell_Bench_Press

# 独立的组，绑定一个训练动作
class ExerciseSetCreate(BaseModel):
    exercise_id: int   # 第二步生成的 PlanExercise 的 ID
    weight: float           # 重量
    reps: int               # 次数
    peak_hr: Optional[int] = None  # 这一组的最高心率
    rest_hr: Optional[int] = None  # 这一组的静心心率
    score:  Optional[int] = None  # 这一组的疲劳评分


class ExerciseSetOut(BaseModel):
    set_id : int # 第三步生成的 set 的 ID
    weight: float  # 重量
    reps: int  # 次数
    peak_hr: Optional[int] = None  # 这一组的最高心率
    rest_hr: Optional[int] = None  # 这一组的静心心率
    score: Optional[int] = None  # 这一组的疲劳评分