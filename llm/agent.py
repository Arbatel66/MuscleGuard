from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from llm.llm_client import LLM_Client
from llm.prompt import SYSTEM_PROMPT
from llm.tool_executor import execute_tool
from models.Plan_Exercise_Model import ExerciseSet
from services.user_service import UserService
from services.fatigue_service import FatigueAnalyzer
from llm.tools import TOOLS
import json

class FitnessAgent:
    def __init__(self, llm_client: LLM_Client):
        self.llm_client = llm_client
        self.system_prompt = SYSTEM_PROMPT

    async def run_analyze(
        self,
        db: AsyncSession,
        session_id: str,
        fatigue_analyzer: FatigueAnalyzer,
        current_set: ExerciseSet
    ) -> Optional[str]:
        """
        调用LLM生成训练建议
        """
        try:


            fatigue_context = fatigue_analyzer.generate_fatigue_context()
            user_context = await UserService.generate_user_context(db=db, session_id=session_id)

            user_message = "请根据以下数据为用户提供训练建议：\n"
            user_message += f"生理指标：{fatigue_context['physiological_metrics']}\n"
            user_message += f"用户信息：{user_context['user_context']}\n"

            # 追加本组训练数据（如果有）
            if any(v is not None for v in [current_set.reps, current_set.weight, current_set.rest_hr]):
                user_message += "本组训练数据：\n"
                if current_set.weight is not None:
                    user_message += f"  - 重量：{current_set.weight} kg\n"
                if current_set.reps is not None:
                    user_message += f"  - 完成次数：{current_set.reps} 次\n"
                if current_set.rest_hr is not None:
                    user_message += f"  - 休息后心率：{current_set.rest_hr} BPM\n"

            user_message += "请按照指定的输出格式提供分析和建议。"

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
            for round_num in range(3):
                print(f"\n🔄 Agent 第 {round_num + 1} 轮推理...")
                response = self.llm_client.think_with_tools(messages, TOOLS)
                msg = response.choices[0].message

                # 没有工具调用 → 直接返回最终答案
                if not msg.tool_calls:
                    print("✅ LLM 直接返回最终答案")
                    return msg.content

                    # 有工具调用 → 执行工具，把结果追加进 messages
                messages.append(msg)
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    print(f"🔧 调用工具: {tool_name}，参数: {args}")
                    #把获取到的工具名和参数传入工具执行器
                    result = await execute_tool(tool_name, args)
                    print(f"📊 工具结果: {result}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })
                    # 超过最大轮数，强制返回最后一条内容
            print("⚠️ 达到最大推理轮数，强制返回")
            return messages[-1].get("content", "分析超时，请重试")
        except Exception as e:
                print(f"❌ Agent 运行出错: {e}")
                return None
