#1.State定义
from typing import TypedDict, Annotated
import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession
from llm.langGraph.lg_tools import calculate_1rm, search_exercise_knowledge, \
    get_exercise_history, get_plan_history, get_sets_detail_by_plan_id
from llm.analysis_prompt import ANALYSIS_SYSTEM_PROMPT
from llm.chat_prompt import CHAT_SYSTEM_PROMPT
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
    tool_calls = getattr(response, "tool_calls", [])

    if tool_calls:
        # 提取所有工具的名字
        tool_names = [tc["name"] for tc in tool_calls]
        print(f"🛠️ [LLM节点] 准备调用工具: {', '.join(tool_names)}")
    else:
        print(f"🧠 [LLM节点] 未触发工具调用，直接回复。")

    return {"messages": [response]}
# 3.Graph构建
def create_fitness_graph(tools, checkpointer = None):
    """
     构建 ReAct 图：
     START → agent → (条件边) → action(工具) → agent → ... → END
     checkpointer: 传入后自动持久化对话历史，实现组间上下文记忆
     """
    workflow = StateGraph(AgentState)

    workflow.add_node("agent",call_model)  # 创建一个llm推理节点
    workflow.add_node("action",ToolNode(tools)) #工具调用节点

    workflow.set_entry_point("agent")
    # Conditional_Edge_1: tools_condition为内置路由函数,是一个判断条件
    workflow.add_conditional_edges("agent",tools_condition,{"tools":"action",END:END})

    # Edge_2 工具执行完成后，固定跳回 agent 继续推理
    workflow.add_edge("action", "agent")

    return workflow.compile(checkpointer = checkpointer)

# 4. 对外入口类（接口不变）
class LGFitnessAgent:
    def __init__(self):
        load_dotenv()

        base_llm = ChatOpenAI(model=os.getenv("LLM_MODEL_ID"),
                          api_key=os.getenv("LLM_API_KEY"),
                          base_url=os.getenv("LLM_BASE_URL"),
                          temperature=0, )
        self._base_llm =  base_llm
        self.db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")

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
        current_set:ExerciseSet,
        plan_id:int,
    ) -> str:
        # 准备tools和LLM
        tools = [calculate_1rm, get_plan_history, get_exercise_history, search_exercise_knowledge, get_sets_detail_by_plan_id]

        llm = self._base_llm.bind_tools(tools)

        # 准备用户消息
        user_ctx = await UserService.generate_user_context(db=db, session_id=session_id)
        user_prompt = self._build_user_prompt(fatigue_analyzer, user_ctx, current_set)

        # 运行（通过 config 注入 llm）。每一次训练计划共用一组上下文记忆
        config = {
            "configurable": {
                "llm": llm,
                "thread_id": str(plan_id),
                "db_session": db,
                "session_id": session_id
            }
        }
        print("\n🚀 LangGraph Agent 开始运行...")
        print("📌 [1] 准备创建 checkpointer 连接...")  # ← 加这行
        #创建checkpointer
        print(f"📌 [2] DB_URL = {self.db_url}")  # ← 加这行
        async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
            print("📌 [3] checkpointer 连接成功")  # ← 加这行
            # 构建图
            app = create_fitness_graph(tools, checkpointer=checkpointer)
            print("📌 [4] Graph构建成功")  # ← 加这
            history = await checkpointer.aget({"configurable": {"thread_id": str(plan_id)}})
            is_first_set = (
                history is None
                or not history.get("channel_values", {}).get("messages")
            )
            if is_first_set:
                print("📝 [Memory] 首次调用，注入 SystemMessage")
                input_messages = [
                    SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            else:
                existing_count = len(history["channel_values"]["messages"])
                print(f"📝 [Memory] 已有 {existing_count} 条历史消息，追加 HumanMessage")
                input_messages = [HumanMessage(content=user_prompt)]

            # 调用app.ainvoke时自动去config找thread_id然后去找对应的checkpointer的历史记录并合并
            final_state = await app.ainvoke(
                {"messages": input_messages},
                config=config,
            )

        print("✅ LangGraph Agent 完成")
        # 从后往前找第一条有实际内容的 AIMessage（避免取到空 content 的 tool_calls 消息）
        from langchain_core.messages import AIMessage
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return ""

    async def lg_chat(
        self,
        db: AsyncSession,
        session_id: str,
        user_message: str,
        ) -> str:

        # 准备tools和LLM
        tools = [calculate_1rm, get_plan_history, get_exercise_history, search_exercise_knowledge, get_sets_detail_by_plan_id]
        llm = self._base_llm.bind_tools(tools)


        config = {
            "configurable": {
                "llm": llm,
                "thread_id": f"chat_{session_id}",
                "db_session": db,
                "session_id": session_id
            }
        }

        async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
            app = create_fitness_graph(tools, checkpointer=checkpointer)

            history = await checkpointer.aget({"configurable": {"thread_id": f"chat_{session_id}"}})
            is_new = (
                    history is None
                    or not history.get("channel_values", {}).get("messages")
            )
            if is_new:
                input_messages = [
                    SystemMessage(content=CHAT_SYSTEM_PROMPT),
                    HumanMessage(content=user_message),
                ]
            else:
                existing_count = len(history["channel_values"]["messages"])
                print(f"📝 [Chat_Memory] 已有 {existing_count} 条历史聊天消息，追加 HumanMessage")
                input_messages = [HumanMessage(content=user_message)]

            # 调用app.ainvoke时自动去config找thread_id然后去找对应的checkpointer的历史记录并合并
            final_state = await app.ainvoke(
                {"messages": input_messages},
                config=config,
            )

        print("✅ LangGraph Agent 完成")
        # 从后往前找第一条有实际内容的 AIMessage（避免取到空 content 的 tool_calls 消息）
        from langchain_core.messages import AIMessage
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return ""



    async def clear_thread(self, thread_id: str):
        """
        物理删除 Postgres 数据库中特定 thread_id 的所有历史记录
        """
        import psycopg

        print(f"🧹 正在准备清空 Thread: {thread_id} ...")

        async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (thread_id,)
                )
                await cur.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (thread_id,)
                )
                await cur.execute(
                    "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                    (thread_id,)
                )
            await conn.commit()

        print(f"✅ Thread {thread_id} 已成功物理清空。")