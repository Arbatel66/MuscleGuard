import httpx
import asyncio
from datetime import datetime
import time
from schemas.SessionManager import HeartRateSample


async def get_current_hr(session_id: str) -> str:
    HYPERATE_URL = f"https://rest.hyperate.io/{session_id}"
    async with httpx.AsyncClient() as client:
        try:
            #     发送请求
            response = await client.get(HYPERATE_URL)
            if response.status_code == 200:
                data = response.json()
                hr_value = data.get("last_heartbeat", 0)
        except Exception as e:
            print(f"数据采集异常:{e}")

        return hr_value
class HeartRateSyncService:
    def __init__(self):
        self.can_run = asyncio.Event()
        self.can_run.clear()  #初始化为"红灯"状态
        self.last_value = -1
        self.current_sample: list[HeartRateSample] = []
        self.current_session_id = ""
        self.start_time = None

    async def create_polling(self, session_id:str):
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
        self.can_run.clear()  # 变红灯：暂停

    def resume_polling(self):
        self.can_run.set()  # 变绿灯：继续

