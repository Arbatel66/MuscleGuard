from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel, JSON, Column
from sqlalchemy.dialects.postgresql import JSONB

# 0. 动作标准库 (由 exercise.json 录入)
# ==========================================
class BaseExercise(SQLModel, table=True):
    __tablename__ = "base_exercise"
    # 使用 JSON 中的 id (如 "3_4_Sit-Up") 作为主键
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    force: Optional[str] = None
    level: Optional[str] = None
    mechanic: Optional[str] = None
    equipment: Optional[str] = None
    category: Optional[str] = None

    # PostgreSQL 特有的 JSONB 存储数组
    primary_muscles: List[str] = Field(default=[], sa_column=Column(JSONB))
    secondary_muscles: List[str] = Field(default=[], sa_column=Column(JSONB))
    instructions: List[str] = Field(default=[], sa_column=Column(JSONB))
    images: List[str] = Field(default=[], sa_column=Column(JSONB))

    # 关系：这个标准动作被哪些计划引用了
    plan_references: List["PlanExercise"] = Relationship(back_populates="base_info")

# 1. 计划表 (Top Level)
class WorkoutPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)  # 你的唯一用户标识
    plan_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    plan_summary: Optional[str] = Field(default=None)
    # 关系：一个计划有多个动作
    exercises: List["PlanExercise"] = Relationship(back_populates="plan")

# 2. 动作表
class PlanExercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="workoutplan.id")

    # 【核心修改】：不再直接存 exercise_name，而是存 standard_id
    # 强制关联到标准库的 id
    exercise_base_id: str = Field(foreign_key="base_exercise.id")
    order_index: Optional[int] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # 关系
    plan: "WorkoutPlan" = Relationship(back_populates="exercises")
    sets: List["ExerciseSet"] = Relationship(back_populates="exercise")

    # 方便直接通过 plan_exercise.base_info.name 获取中文名或图片
    base_info: BaseExercise = Relationship(back_populates="plan_references")

# 3. 组数表 (Data Level)
class ExerciseSet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    exercise_id: int = Field(foreign_key="planexercise.id")
    weight: float
    reps: int
    peak_hr: int
    rest_hr: int
    score : int
    created_at: datetime = Field(default_factory=datetime.now)

    # 关系
    exercise: PlanExercise = Relationship(back_populates="sets")