## MuscleGuard 项目完整复盘

---

### 一、项目定位

MuscleGuard 是一个 AI 驱动的健身训练助手，核心亮点是：用户佩戴心率设备（HypeRate），每完成一组训练后，系统自动采集心率数据、计算疲劳评分，并调用 LLM Agent 给出有数据支撑的训练建议。

---

### 二、技术栈总览

| 层级       | 技术                                                                                |
| ------------ | ------------------------------------------------------------------------------------- |
| 后端框架   | FastAPI + Uvicorn（异步，Windows 强制 `SelectorEventLoop`）                     |
| 数据库     | PostgreSQL（异步驱动 `asyncpg`，ORM 用 `SQLModel` = SQLAlchemy + Pydantic） |
| LLM 框架   | LangGraph（ReAct Agent）+ LangChain + OpenAI 兼容接口                               |
| 记忆持久化 | `AsyncPostgresSaver`（LangGraph checkpoint 存 PostgreSQL）                      |
| RAG 向量库 | ChromaDB + HuggingFace `paraphrase-multilingual-MiniLM-L12-v2`                  |
| 心率数据源 | HypeRate REST API（轮询，每 2 秒一次）                                              |
| 前端       | Next.js 14（App Router）+ TypeScript + shadcn/ui                                    |

---

### 三、数据库模型关系

User (session_id PK)

│

└── WorkoutPlan (session_id FK)          ← 一次训练计划

```
│


    └── PlanExercise (plan_id FK)      ← 计划内的某个动作


          │   └── exercise_base_id FK ──→ BaseExercise (标准动作库)


          │


          └── ExerciseSet             ← 某动作的一组数据


                weight / reps / peak_hr / rest_hr / score
```

`BaseExercise` 是从 `exercise.json`（free-exercise-db）导入的标准动作库，存储动作名、肌肉群、器械、教程等，使用 PostgreSQL `JSONB` 存数组字段。

---

### 四、完整业务流程

#### 阶段 0：启动（lifespan）

FastAPI 启动

→ 加载 .env

→ 初始化 HeartRateSyncService（心率服务单例）

→ 初始化 LGFitnessAgent（LLM Agent 单例）

→ create_db_and_tables()（建表）

→ AsyncPostgresSaver.setup()（建 checkpoint 相关表）

---

#### 阶段 1：用户登录 / 注册

前端 LoginScreen

→ POST /user/{session_id}  检查是否已注册

```
├── 已存在 → 直接进入训练计划页


  └── 不存在 → 进入 RegisterCard


                → POST /user/create  写入 User 表
```

* `session_id` 直接用 HypeRate App 提供的设备 ID，一物两用（心率设备 + 用户标识）

---

#### 阶段 2：开始轮询心率

前端登录成功后立即调用

→ POST /sync/create_polling?session_id=xxx

```
→ asyncio.create_task(HeartRateSyncService.create_polling)


      → 每 2s 请求 https://rest.hyperate.io/{session_id}


      → 存入 self.current_sample[]（HeartRateSample 列表）


      → 更新 self.last_value


      → 初始状态：can_run=False（红灯，暂停状态）
```

---

#### 阶段 3：创建训练计划

前端 PlanSetupScreen

→ POST /exercise/create_plan  { plan_name, session_id }

```
→ PlanService.create_plan() → 写入 WorkoutPlan 表


  → 返回 plan_id 给前端（后续全程使用）
```

---

#### 阶段 4：选择肌肉部位 → 选择动作

前端 MuscleSelectScreen

→ GET /exercise/muscles_list

```
→ PostgreSQL jsonb_array_elements 展开所有肌肉去重
```

前端 ExerciseSelectScreen

→ GET /exercise/exercise_list?muscle=xxx

```
→ BaseExercise.primary/secondary_muscles JSONB contains 查询
```

前端确认动作列表后

→ POST /exercise/add_exercises  { plan_id, exercise_base_id }

```
→ ExerciseService.create_exercise() → 写入 PlanExercise 表


  → 返回 exercise_id 给前端
```

---

#### 阶段 5：训练中 —— 每完成一组的核心流程

这是整个系统最核心的环节：

用户开始做这组:

→ POST /sync/resume_polling

```
→ can_run.set()（绿灯，开始采集心率）


  → 重置 start_time
```

用户完成这组后点击"完成":

→ POST /sync/pause_polling  { exercise_id, weight, reps }

```
┌─── 1. HeartRateSyncService.pause_polling()


  │        can_run.clear()（红灯，停止采集）


  │


  ├─── 2. FatigueAnalyzer 计算疲劳评分


  │        peak_hr = max(current_sample[].hr)


  │        rest_hr = last_value（当前心率，即休息后心率）


  │        rec_score = _compute_recovery_60s_score()


  │            HRR% = (peak - rest) / peak


  │            >= 18% → 10分（恢复好）


  │            >= 12% → 40分（恢复中）


  │            <  12% → 70分（恢复差）


  │        hist_score = compute_history_exercise_peak_score()


  │            HR效率 = peak_hr / (weight/1RM * 100)


  │            与历史均值比，超出30%则附加30分


  │        total_score = rec_score + hist_score  (0~100，越高越疲劳)


  │


  ├─── 3. SetsService.create_set() → 写入 ExerciseSet 表


  │


  └─── 4. LGFitnessAgent.lg_run_analysis()


           ┌── 构建用户 Prompt（疲劳数据 + 用户信息 + 本组数据）


           ├── 从 PostgreSQL checkpoint 读历史消息（同 plan_id = 同 thread）


           ├── 首组：注入 SystemMessage(ANALYSIS_SYSTEM_PROMPT) + HumanMessage


           │   后续组：只追加 HumanMessage（利用历史记忆）


           ├── ReAct Graph 推理：


           │     agent(LLM) → 判断是否需要工具


           │       ├── calculate_1rm(weight, reps) → Epley公式


           │       ├── get_exercise_history(exercise_id) → 历史组数对比


           │       ├── get_plan_history() → 历史计划列表


           │       ├── get_sets_detail_by_plan_id(plan_id) → 计划详细数据


           │       └── search_exercise_knowledge(query) → RAG检索


           │               ├── exercises 向量库（exercise.json）MMR检索 k=10


           │               └── champion_book 向量库（PDF→MD）MultiQuery检索 k=5


           └── 返回 AI 分析文字 → 前端展示
```

---

#### 阶段 6：AI 对话（独立入口）

前端聊天界面

→ POST /chat/ai_chat  { session_id, message }

```
→ 每次先清空 thread "chat_12A3C"（当前写死，TODO）


  → LGFitnessAgent.lg_chat()


      → 同样的 ReAct Graph


      → thread_id = "chat_{session_id}"（独立于训练记忆）


      → SystemMessage 用 CHAT_SYSTEM_PROMPT（更偏对话式）


      → 可用同一套工具查询训练历史 / RAG 知识
```

---

### 五、RAG 知识库架构

两个 ChromaDB Collection：

┌── "exercises"

│     数据源：db/exercise.json（标准动作库 ~860 条）

│     Embedding：paraphrase-multilingual-MiniLM-L12-v2

│     检索：MMR，k=10，fetch_k=30

│

└── "champion_book"

```
数据源：PDF → marker 解析 → Markdown


           → MarkdownHeaderTextSplitter（按 #/##/###/#### 切）


           → RecursiveCharacterTextSplitter（chunk=600, overlap=120）


    检索：MultiQueryRetriever（LLM 扩写查询）+ MMR，k=5
```

`ingest_pdf.py` 是离线工具：用 `marker` 库（支持 GPU）将 PDF 转成 Markdown，供 `_load_markdown()` 读取入库。

---

### 六、LangGraph ReAct 图结构

START

│

▼

[agent] ← call_model(state, config)

│         llm 从 config["configurable"]["llm"] 注入

│

├── 有 tool_calls → [action] (ToolNode)

│                      │

│                      └── 执行工具 → 回到 [agent]

│

└── 无 tool_calls → END

checkpointer = AsyncPostgresSaver

→ 每次 ainvoke 自动持久化消息到 PostgreSQL

→ thread_id = plan_id（训练）或 "chat_{session_id}"（聊天）

---

### 七、前端页面状态机

"login"

├── 登录成功 → "plan-setup"

└── 未注册 → "register"

