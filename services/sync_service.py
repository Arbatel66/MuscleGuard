import httpx
import asyncio
from datetime import datetime
import time
from schemas.SessionManager import HeartRateSample

class UserHeartRateState:
    """每个用户独立的心率状态"""
    def __init__(self):
        self.can_run = asyncio.Event()
        self.can_run.clear()
        self.last_value: int = -1
        self.current_sample: list[HeartRateSample] = []
        self.session_id :str = ""
        self.start_time = None

    async def create_polling(self, session_id: str):
        self.session_id = session_id
        print(f"self.session_id: {self.session_id}")
        HYPERATE_URL = f"https://rest.hyperate.io/{session_id}"
        print(f"数据是{HYPERATE_URL}")
        async with httpx.AsyncClient() as client:
            while True:
                await self.can_run.wait()
                try:
                    #     发送请求
                    response = await client.get(HYPERATE_URL)
                    if response.status_code == 200:
                        data = response.json()
                        hr_value = data.get("last_heartbeat", 0)

                    self.last_value = hr_value
                    # 2. 计算秒数偏移
                    if self.start_time is None:
                        self.start_time = time.time()
                    elapsed = int(time.time() - self.start_time)
                    # 3. 创建 Pydantic 对象并存入列表
                    sample = HeartRateSample(t=elapsed, hr=hr_value)
                    self.current_sample.append(sample)
                    print(f"[{elapsed}] 采集到有效心率: {hr_value} BPM")
                except Exception as e:
                    print(f"数据采集异常:{e}")
                await asyncio.sleep(2)

    def pause_polling(self):
        self.can_run.clear()

    def resume_polling(self):
        self.can_run.set()  # 变绿灯：继续


class HeartRateSyncService:
    def __init__(self):
       self._states:dict[str,UserHeartRateState]  = {}

    def get_or_create(self, session_id:str) -> UserHeartRateState:
        if session_id not in self._states:
            self._states[session_id] = UserHeartRateState()
        return self._states[session_id]

