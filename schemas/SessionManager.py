from pydantic import BaseModel
from typing import List

# 定义单个数据点的结构
class HeartRateSample(BaseModel):
    t: int   # 偏移秒数
    hr: int  # 心率值

# 定义整组训练的结构
class TrainingSessionData(BaseModel):
    session_id: str
    samples: List[HeartRateSample]