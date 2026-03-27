#1.State定义
from typing import TypedDict, Annotated
import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.constants import END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession
from llm.langGraph.lg_tools import calculate_1rm, make_exercise_history_tool
from llm.prompt import SYSTEM_PROMPT
from models.Plan_Exercise_Model import ExerciseSet
from services.fatigue_service import FatigueAnalyzer
from services.user_service import UserService


# 1. STATE 定义
#    图中所有节点共享这个数据结构
#    add_messages 是 reducer：每次写入是追加而非覆盖
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 完整消息历史


# 2. NODE 定义
#    每个节点 = 一个函数，接收 State，返回 State 的局部更新
async def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """
    节点1 - LLM 推理节点
    从 config 中取已绑定工具的 llm，调用推理，返回 AI 回复
    """
    llm = config["configurable"]["llm"]
    print(f"🧠 [LLM节点] 消息数: {len(state['messages'])}，正在推理...")
    response = await llm.ainvoke(state["messages"])
    print(f"🧠 [LLM节点] 是否有工具调用: {bool(getattr(response, 'tool_calls', None))}")
    return {"messages": [response]}

# 3.Graph构建
def create_fitness_graph(tools):
    """
     构建 ReAct 图：
     START → agent → (条件边) → action(工具) → agent → ... → END
     """
    workflow = StateGraph(AgentState)

    workflow.add_node("agent",call_model)  # 创建一个llm推理节点
    workflow.add_node("action",ToolNode(tools)) #工具调用节点

    workflow.set_entry_point("agent")
    # Conditional_Edge_1: tools_condition为内置路由函数
    workflow.add_conditional_edges("agent",tools_condition,{"tools":"action",END:END})

    # Edge_2 工具执行完成后，固定跳回 agent 继续推理
    workflow.add_edge("action", "agent")

    return workflow.compile()

# 4. 对外入口类（接口不变）
class LGFitnessAgent:
    def _build_user_prompt(self, fatigue_analyzer: FatigueAnalyzer,user_ctx: dict, current_set:ExerciseSet) ->str:
        fatigue_context = fatigue_analyzer.generate_fatigue_context()
        msg = "请根据以下数据为用户提供训练建议：\n"
        msg += f"生理指标：{fatigue_context['physiological_metrics']}\n"
        msg += f"用户信息：{user_ctx['user_context']}\n"

        # 追加本组训练数据（如果有）
        if any(v is not None for v in [current_set.reps, current_set.weight, current_set.rest_hr]):
            msg += "本组训练数据：\n"
            if current_set.weight is not None:
                msg += f"  - 重量：{current_set.weight} kg\n"
            if current_set.reps is not None:
                msg += f"  - 完成次数：{current_set.reps} 次\n"
            if current_set.rest_hr is not None:
                msg += f"  - 休息后心率：{current_set.rest_hr} BPM\n"
            if current_set.exercise_id is not None:
                msg += f"  - 当前exercise_id：{current_set.exercise_id} \n"
        msg += "请按照指定的输出格式提供分析和建议。"
        return msg


    async def lg_run_analysis(
        self,
        db: AsyncSession,
        session_id: str,
        fatigue_analyzer: FatigueAnalyzer,
        current_set:ExerciseSet
    ) -> str:
        # 准备tools和LLM
        tools = [calculate_1rm,make_exercise_history_tool(db)]
        load_dotenv()
        llm = (ChatOpenAI(model=os.getenv("LLM_MODEL_ID"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0,)
            .bind_tools(tools))

        # 构建图
        app = create_fitness_graph(tools)

        # 准备用户消息
        user_ctx = await UserService.generate_user_context(db=db, session_id=session_id)
        user_prompt = self._build_user_prompt(fatigue_analyzer, user_ctx, current_set)

        # 运行（通过 config 注入 llm）
        config = {"configurable": {"llm": llm, "thread_id": session_id}}
        print("\n🚀 LangGraph Agent 开始运行...")

        final_state = await app.ainvoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            },
            config=config,
        )

        print("✅ LangGraph Agent 完成")
        return final_state["messages"][-1].content