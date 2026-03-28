from pydantic import BaseModel
from typing import List

# 定义单个数据点的结构
class HeartRateSample(BaseModel):
    t: int   # 偏移秒数
    hr: int  # 心率值

class ChatRequest(BaseModel):
    session_id: str
    message: str

