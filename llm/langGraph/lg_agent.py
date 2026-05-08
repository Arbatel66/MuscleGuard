#1.State定义
from typing import TypedDict, Annotated
import os
import asyncio
import logging

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage, trim_messages
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.constants import END
from langgraph.graph import add_messages, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session, async_session_factory
from llm.langGraph.lg_tools import calculate_1rm, search_exercise_knowledge, \
    get_exercise_history, get_plan_history, get_sets_detail_by_plan_id, get_current_time
from llm.analysis_prompt import ANALYSIS_SYSTEM_PROMPT
from llm.chat_prompt import CHAT_SYSTEM_PROMPT
from llm.rag.chroma_service import ChromaService
from llm.rag.rag_retriever import search_summaries
from llm.schemas.MemorySummaryPayload import MemorySummaryPayload
from llm.summary_prompt import SUMMARY_SYSTEM_PROMPT
from models.Plan_Exercise_Model import ExerciseSet
from services.agent_service import AgentService
from services.fatigue_service import FatigueAnalyzer
from services.user_service import UserService
from services.plan_service import PlanService
from deepseek_tokenizer import ds_token

CHAT_CONTEXT_WINDOW_TOKENS = 6000
SUMMARY_ACTIVE_WINDOW_TOKENS = 2500
SUMMARY_TRIGGER_UNSUMMARIZED_MESSAGES = 24
SUMMARY_TRIGGER_UNSUMMARIZED_TOKENS = 5000
SUMMARY_TRIGGER_MIN_SLIDE_OUT_TOKENS = 1000

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO, # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # 时间、名字、级别、消息
    handlers=[
        logging.FileHandler(f"{log_dir}/muscle_guard.log", encoding='utf-8'), # 存到文件，支持中文
        logging.StreamHandler() # 同时在控制台打印
    ]
)

logger = logging.getLogger("FitnessAgent")

def deepseek_token_counter(messages: list[BaseMessage]) -> int:
    # 将消息列表拼接成一个字符串，你可以根据你的消息格式进行调整
    text = "".join([msg.content for msg in messages if msg.content])
    # 直接调用官方方法计算 token 数量
    return len(ds_token.encode(text))

def messages_transcript(messages: list) -> str:
    rows = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "human"
        elif isinstance(msg, AIMessage):
            role = "ai"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            role = "message"
        content = msg.content
        if isinstance(content, list):
            content = " ".join(str(x) for x in content)
        if content:
            rows.append(f"[{role}] {content}")
    return "\n".join(rows)



# 1. STATE 定义
#    图中所有节点共享这个数据结构
#    add_messages 是 reducer：每次写入是追加而非覆盖
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]# 完整消息历史
    scope: str
    summaries :list[str]
    last_summarized_id :str

# 2. NODE 定义
#    每个节点 = 一个函数，接收 State，返回 State 的局部更新
async def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """
    节点1 - LLM 推理节点
    从 config 中取已绑定工具的 llm，调用推理，返回 AI 回复
    """
    llm = config["configurable"]["llm"]
    scope = state["scope"]

    summaries = state.get("summaries", [])
    summary_context = "\n".join([f"- {s}" for s in summaries]) if summaries else "暂无历史背景。"

    full_system_content = (
        f"{CHAT_SYSTEM_PROMPT}\n\n"  
        f"### 用户长期记忆档案 ###\n"
        f"{summary_context}"
    )
    current_system_message = SystemMessage(content=full_system_content)

    # 根据scope划分消息滑动窗口范围
    if scope == "chat":
        trimmer = trim_messages(
            max_tokens= CHAT_CONTEXT_WINDOW_TOKENS,
            strategy="last",
            token_counter=deepseek_token_counter,
            include_system=False,
            start_on="human",
            allow_partial=False,
        )
        pure_chat_history = [
            m for m in state["messages"]
            if not isinstance(m, SystemMessage)
        ]
        print(f"判断为[chat]模式，调用滑动窗口")
        trimmed_messages = trimmer.invoke(pure_chat_history)
        print(f"✂️ 裁剪前: {len(state['messages'])} 条, 裁剪后: {len(trimmed_messages)} 条")
        model_messages = [current_system_message] + trimmed_messages

    else:
        print("判断为[analysis]模式")
        full_messages = [
            m for m in state["messages"]
            if not isinstance(m, SystemMessage)
        ]
        current_system_message = SystemMessage(content=ANALYSIS_SYSTEM_PROMPT)
        model_messages = [current_system_message] + full_messages

    print(f"🧠 [LLM节点] 消息数: {len(model_messages)}，正在推理...")
    response = await llm.ainvoke(model_messages)
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
        # 状态锁，只用来去重，不存储总结。判断当前是否触发总结了，若正在总结则不触发下一次总结。
        self._summary_tasks: set[str] = set()

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

    def _get_unsummarized_messages(self, state: dict) -> list[BaseMessage]:
        pure_chat_history = [
            m for m in state.get("messages", [])
            if not isinstance(m, SystemMessage)
        ]

        last_summarized_id = state.get("last_summarized_id")
        if not last_summarized_id:
            return pure_chat_history

        for index, msg in enumerate(pure_chat_history):
            if msg.id == last_summarized_id:
                return pure_chat_history[index + 1:]

        return pure_chat_history

    def _should_trigger_summary(self, state: dict) -> tuple[bool, dict]:
        """
        只有当“未总结消息数量够多”且“活跃窗口外真的有足够内容值得总结”，或者“未总结 token 总量已经很大”时，才触发后台总结
        """
        unsummarized_messages = self._get_unsummarized_messages(state)
        unsummarized_message_count = len(unsummarized_messages)
        unsummarized_tokens = deepseek_token_counter(unsummarized_messages)
        slide_out_tokens = max(0, unsummarized_tokens - SUMMARY_ACTIVE_WINDOW_TOKENS)

        should_trigger = (
                (
                        unsummarized_message_count >= SUMMARY_TRIGGER_UNSUMMARIZED_MESSAGES
                        and slide_out_tokens >= SUMMARY_TRIGGER_MIN_SLIDE_OUT_TOKENS
                )
                or unsummarized_tokens >= SUMMARY_TRIGGER_UNSUMMARIZED_TOKENS
        )

        return should_trigger, {
            "unsummarized_message_count": unsummarized_message_count,
            "unsummarized_tokens": unsummarized_tokens,
        }


    async def _check_and_summarize(self, state: dict, config: dict):
        """
        后台执行总结逻辑：判断 Token 长度并存入 DB 和 Chroma
        """
        try:
            llm = config["configurable"]["llm"]
            pure_chat_history = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
            if not pure_chat_history:
                return
            # 2. 计算当前需要保留的活跃区 (最近 2000 Token)
            incremental_trimmer = trim_messages(
                max_tokens= SUMMARY_ACTIVE_WINDOW_TOKENS,
                strategy="last",
                token_counter=deepseek_token_counter,
                include_system=False,
                start_on="human",
                allow_partial=False
            )

            active_messages = incremental_trimmer.invoke(pure_chat_history)
            if not active_messages:
                return

            # 活跃区的起点 ID，这是我们抓取滑出消息的“终点”边界
            active_start_id = active_messages[0].id

            # 3. 利用游标找出“未总结的滑出消息”
            last_summarized_id = state.get("last_summarized_id")
            unsummarized_slide_out = []
            capture = False

            # 如果是第一次总结，或者找不到锚点，就从头开始抓取
            if not last_summarized_id:
                capture = True

            for msg in pure_chat_history:
                if msg.id == active_start_id:
                    break  # 碰到活跃区的边界，停止抓取
                if capture:
                    unsummarized_slide_out.append(msg)
                elif msg.id == last_summarized_id:
                    # 碰到上次总结的最后一条消息，说明从下一条开始是新消息
                    capture = True

            if not unsummarized_slide_out:
                logger.info("ℹ️ [Memory] 当前没有新的滑出消息需要总结，跳过。")
                return

            slide_out_text = messages_transcript(unsummarized_slide_out)
            logger.info(f"🔄 [Memory] 找到 {len(unsummarized_slide_out)} 条新滑出消息，开始滚动融合总结...")

            # 4. 提取 L2 历史总结
            last_summaries = state.get("summaries", [])
            last_summary_text = last_summaries[0] if last_summaries else "尚无历史背景"

            # 5. 调用 LLM 生成最新的滚动总结
            prompt_content = (
                f"【已有历史核心总结】:\n{last_summary_text}\n\n"
                f"【最新产生的对话记录】:\n{slide_out_text}\n\n"
                f"请将上述两部分信息进行逻辑整合，生成最新的核心要点总结。"
                f"注意：提取关键的训练数据、生理反馈及计划变更，忽略寒暄。"
            )

            structured_llm = llm.with_structured_output(
                MemorySummaryPayload,
                method='json_mode'
            )
            summary_result = await structured_llm.ainvoke([
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=prompt_content)
            ])

            payload_dict = summary_result.model_dump()
            new_summary_text = AgentService.summary_json_to_text(payload_dict)

            session_id = config["configurable"]["session_id"]
            thread_id = config["configurable"]["thread_id"]
            source_message_count = len(state["messages"])
            async with async_session_factory() as db:
                record = await AgentService.save_summary_to_db(
                    db,
                    session_id=session_id,
                    thread_id=thread_id,
                    scope=state["scope"],
                    source_message_count=source_message_count,
                    summary_payload=payload_dict
                )
            await ChromaService.save_summaries_to_chroma(record)
            print(f"✅ [Memory] 总结已存入向量库，ID: {record.id}")

            new_last_id = unsummarized_slide_out[-1].id
            async with AsyncPostgresSaver.from_conn_string(self.db_url) as bg_checkpointer:
                bg_app = create_fitness_graph(tools=[], checkpointer=bg_checkpointer)
                await bg_app.aupdate_state(
                    config,
                    {
                        "summaries": [new_summary_text],
                        "last_summarized_id": new_last_id
                    }
                )
            logger.info(f"✅ [Memory] Checkpoint 状态更新完毕，最新游标已停留在 ID: {new_last_id}")
        except Exception:
            # 记录日志，这是“即发即弃”模式唯一的补救手段
            logger.exception("Background summary task failed")

    async def lg_run_analysis(
        self,
        db: AsyncSession,
        session_id: str,
        fatigue_analyzer: FatigueAnalyzer,
        current_set:ExerciseSet,
        plan_id:int,
    ) -> str:
        # 准备tools和LLM
        tools = [calculate_1rm, get_plan_history, get_exercise_history, search_exercise_knowledge, get_sets_detail_by_plan_id, search_summaries, get_current_time]

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

        #创建checkpointer
        async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
            # 构建图
            app = create_fitness_graph(tools, checkpointer=checkpointer)
            history = await checkpointer.aget({"configurable": {"thread_id": str(plan_id)}})
            is_first_set = (
                history is None
                or not history.get("channel_values", {}).get("messages")
            )
            if is_first_set:
                print("📝 [Memory] 首次调用，追加 HumanMessage")
            else:
                existing_count = len(history["channel_values"]["messages"])
                print(f"📝 [Memory] 已有 {existing_count} 条历史消息，追加 HumanMessage")
            input_messages = [HumanMessage(content=user_prompt)]

            # 调用app.ainvoke时自动去config找thread_id然后去找对应的checkpointer的历史记录并合并
            final_state = await app.ainvoke(
                {
                    "messages": input_messages,
                    "scope": "training"
                },
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
        tools = [calculate_1rm, get_plan_history, get_exercise_history, search_exercise_knowledge, get_sets_detail_by_plan_id, search_summaries, get_current_time]
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
            existing_state = history.get("channel_values", {}) if history else {}
            existing_summaries = existing_state.get("summaries")

            input_data = {
                "messages": [HumanMessage(content=user_message)],
                "scope": "chat"
            }
            # 1.每次聊天加载最近三条训练总结
            training_summaries_objs = await AgentService.get_latest_summaries(
                db, session_id, limit=3, scope="training"
            )
            training_summaries = [s.summary_text for s in training_summaries_objs]
            # 2.查找是否有聊天总结缓存
            if existing_summaries:
                chat_summaries = existing_summaries
                print(f"🔄 使用 Checkpoint 中的聊天总结（{len(chat_summaries)} 条）")
            else:
                chat_summaries_objs = await AgentService.get_latest_summaries(
                    db, session_id, limit=3, scope="chat"
                )
                chat_summaries = [s.summary_text for s in chat_summaries_objs]
                print(f"🔍 从数据库加载聊天总结（{len(chat_summaries)} 条）")
            # merge两种总结为input
            combined_summaries = training_summaries + chat_summaries
            input_data["summaries"] = combined_summaries

            print(f"📊 总记忆：{len(training_summaries)} 条训练 + {len(chat_summaries)} 条聊天")

            # 调用app.ainvoke时自动去config找thread_id然后去找对应的checkpointer的历史记录并合并
            final_state = await app.ainvoke(
                input_data,
                config=config,
            )

        print("✅ LangGraph Agent 完成")
        # 从后往前找第一条有实际内容的 AIMessage（避免取到空 content 的 tool_calls 消息）
        ai_response = ""
        actual_usage = {}
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                ai_response = msg.content
                actual_usage = getattr(msg, "usage_metadata", {})
                break

        print(f"📊 [Chat] 本次调用真实 Token 消耗: {actual_usage}")

        should_summarize, summary_stats = self._should_trigger_summary(final_state)
        print(
            f"当前 [Memory] 未总结消息数={summary_stats['unsummarized_message_count']}, "
            f"未总结Token数={summary_stats['unsummarized_tokens']}"
        )

        thread_id = config["configurable"]["thread_id"]

        if should_summarize:
            if thread_id in self._summary_tasks:
                print(f"⏳ [Memory] Thread {thread_id} 已有总结任务进行中，跳过本次触发")
            else:
                print(f"✅ [Memory] 满足阈值，开始为 Thread {thread_id} 生成长期记忆...")
                self._summary_tasks.add(thread_id)

                task = asyncio.create_task(self._check_and_summarize(final_state, config))

                def _on_task_completed(_, tid=thread_id):
                    self._summary_tasks.discard(tid)
                    print(f"🏁 [Memory] Thread {tid} 总结任务已完成并释放锁。")
                task.add_done_callback(_on_task_completed)

        return ai_response

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


    async def lg_summarize_training(
            self,
            db: AsyncSession,
            session_id: str,
            plan_id: int,
    ) -> str:
        """
        训练结束后，对整个 thread_id 的对话历史进行总结
        存入 DB 和向量库，供后续检索使用
        """
        config = {
            "configurable": {
                "thread_id": str(plan_id),
                "session_id": session_id
            }
        }

        async with AsyncPostgresSaver.from_conn_string(self.db_url) as checkpointer:
            # 1. 读取完整对话历史
            history = await checkpointer.aget(config)
            if not history or not history.get("channel_values", {}).get("messages"):
                logger.warning(f"⚠️ [Training Summary] Plan {plan_id} 无对话记录")
                return "无训练记录"

            messages = history["channel_values"]["messages"]
            pure_messages = [m for m in messages if not isinstance(m, SystemMessage)]
            transcript = messages_transcript(pure_messages)

            logger.info(f"📊 [Training Summary] Plan {plan_id} 开始生成总结，消息数: {len(pure_messages)}")

            # 2. 调用 LLM 生成自然语言总结（不使用结构化输出）
            prompt = (
                f"你是 MuscleGuard 的 AI 私教，正在为用户生成本次训练的总结报告。\n\n"
                f"以下是用户本次训练的完整对话记录：\n{transcript}\n\n"
                f"请用自然、亲切的语气生成一份训练总结，就像私教在训练结束后和学员聊天一样。\n\n"
                f"总结要求：\n"
                f"1. 开头简短评价整体表现（如：今天状态不错、完成度很高等）\n"
                f"2. 具体分析每个动作的完成情况（重量、次数、疲劳度）\n"
                f"3. 如果有异常情况（心率数据缺失、疲劳度过高等），用关心的语气提醒\n"
                f"4. 给出下次训练的具体建议（重量调整、组间休息等）\n"
                f"5. 结尾鼓励用户，保持积极的训练氛围\n\n"
                f"语气风格：\n"
                f"- 像朋友一样亲切，不要太正式\n"
                f"- 用「你」而不是「用户」\n"
                f"- 避免使用「标题：」「摘要：」这种格式化标记\n"
                f"- 直接用段落形式，自然流畅\n"
                f"- 可以适当使用 emoji 增加亲和力（但不要过度）\n\n"
                f"直接输出总结内容，不要有任何前缀或格式标记。"
            )

            summary_result = await self._base_llm.ainvoke([
                HumanMessage(content=prompt)
            ])
            
            summary_text = summary_result.content

            # 3. 存入 DB（使用简化的 JSON 格式）
            summary_payload = {
                "title": f"训练总结 - Plan {plan_id}",
                "summary": [summary_text],
                "key_facts": [],
                "injuries": [],
                "preferences": [],
                "goals": [],
                "risks": [],
                "next_focus": []
            }
            
            record = await AgentService.save_summary_to_db(
                db,
                session_id=session_id,
                thread_id=str(plan_id),
                scope="training",
                source_message_count=len(pure_messages),
                summary_payload=summary_payload
            )

            # 4. 存入向量库
            await ChromaService.save_summaries_to_chroma(record)

            # 5. 更新plan中的summary字段
            await PlanService.update_plan_summary(db, plan_id, summary_text)

            logger.info(f"✅ [Training Summary] Plan {plan_id} 总结完成，ID: {record.id}")
            return summary_text