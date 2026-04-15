# MuscleGuard — AI 健身私人教练

基于 **HypeRate** 实时心率数据，结合 **LangGraph ReAct Agent + RAG 知识库**，在每组训练结束后自动分析疲劳状态、给出有数据支撑的训练建议；同时提供独立的 AI 对话教练入口，支持查询历史训练记录与健身动作知识。

---
![77157c3d863ee1efd2dd16b36cf184ba.png](..%2F..%2F%E5%BE%AE%E4%BF%A1%2Fxwechat_files%2Fwxid_5307563081112_52bc%2Ftemp%2FRWTemp%2F2026-03%2F9e20f478899dc29eb19741386f9343c8%2F77157c3d863ee1efd2dd16b36cf184ba.png)
## 技术栈

| 层级 | 技术 |
|---|---|
| **Web 框架** | FastAPI + Uvicorn（异步，Windows 强制 `SelectorEventLoop`）|
| **数据库** | PostgreSQL + asyncpg + SQLModel ORM（SQLAlchemy 2.0 异步）|
| **AI 框架** | LangGraph + LangChain + OpenAI 兼容接口 |
| **对话记忆** | LangGraph `AsyncPostgresSaver`（checkpoint 持久化到 PostgreSQL）|
| **RAG 向量库** | ChromaDB + HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` |
| **PDF 解析** | Marker（GPU 加速，PDF → Markdown）|
| **心率采集** | HypeRate REST API（每 2s 轮询）|
| **前端** | Next.js 14（App Router）+ TypeScript + shadcn/ui |
| **数据验证** | Pydantic v2 |
| **运行环境** | Python 3.12 |

---

## 项目结构

```
MuscleGuard/
├── main.py                  # FastAPI 入口，注册路由，CORS 配置
├── lifespan.py              # 启动/关闭钩子：初始化 DB、Agent、心率服务、checkpoint
├── requirements.txt
│
├── controller/              # 路由层（接收 HTTP 请求）
│   ├── sync.py              # 心率同步 & 组后疲劳分析（核心入口）
│   ├── user.py              # 用户注册/查询
│   ├── exercise.py          # 计划/动作/组数 CRUD
│   └── chat.py              # AI 对话教练入口
│
├── services/                # 业务逻辑层
│   ├── fatigue_service.py   # 疲劳评分算法（HRR + 历史心率效率对比）
│   ├── sync_service.py      # HypeRate 心率实时轮询服务
│   ├── plan_service.py      # 训练计划管理
│   ├── exercise_service.py  # 动作库查询（JSONB 多字段）
│   ├── sets_service.py      # 训练组 CRUD + 多表联查
│   └── user_service.py      # 用户信息 & LLM 上下文生成
│
├── llm/
│   ├── llm_client.py        # OpenAI 兼容客户端封装（流式 + Tool Calling）
│   ├── analysis_prompt.py   # 训练分析 System Prompt
│   ├── chat_prompt.py       # 对话教练 System Prompt
│   ├── agent.py             # 旧版 FitnessAgent（手动 ReAct 循环，已被 LangGraph 替代）
│   ├── tools.py             # 旧版 OpenAI Tool 定义
│   ├── tool_executor.py     # 旧版工具执行器
│   └── langGraph/
│       ├── lg_agent.py      # LangGraph ReAct Agent（训练分析 + 对话双模式）
│       └── lg_tools.py      # Agent 工具：1RM 计算、历史查询、RAG 检索
│
├── llm/rag/
│   ├── exercise_vectorstore.py  # ChromaDB 向量库管理（双 collection 懒加载）
│   ├── rag_retriever.py         # search_exercise_knowledge 工具（MMR + MultiQuery）
│   ├── ingest_pdf.py            # 离线工具：PDF → Markdown（marker + GPU）
│   └── test_RAG.py
│
├── models/                  # SQLModel 数据模型（对应数据库表）
│   ├── User.py
│   └── Plan_Exercise_Model.py   # WorkoutPlan / PlanExercise / ExerciseSet / BaseExercise
│
├── schemas/                 # Pydantic 请求/响应 Schema
│   ├── Workout_schemas.py
│   └── SessionManager.py    # HeartRateSample / ChatRequest
│
├── repositories/
│   └── workout_repository.py    # 四表联查骨架 SQL
│
├── db/
│   ├── database.py          # AsyncSession 工厂，建表
│   ├── init_script.py       # 从 exercise.json 初始化动作库
│   └── exercise.json        # 标准动作种子数据
│
├── data/
│   ├── document/            # PDF 原文 & 解析后 Markdown（RAG 数据源）
│   └── chroma_db/           # ChromaDB 持久化目录
│
├── frontend/                # Next.js 前端
│   ├── app/
│   │   ├── page.tsx         # 主状态机（login→register→plan→muscle→exercise→training）
│   │   └── layout.tsx
│   └── components/
│       ├── login-screen.tsx
│       ├── register-card.tsx
│       ├── plan-setup-screen.tsx
│       ├── muscle-select-screen.tsx
│       ├── exercise-select-screen.tsx
│       ├── training-screen.tsx
│       ├── ai-chat-drawer.tsx   # 悬浮 AI 对话教练（登录后全局挂载）
│       └── ...
│
└── free-exercise-db/        # 开源动作数据集（Git 子模块）
```

---

## 数据模型关系

```
User (session_id PK)
  └── WorkoutPlan (session_id FK)          ← 一次训练计划
        └── PlanExercise (plan_id FK)      ← 计划内的某个动作
              │   └── exercise_base_id FK ──→ BaseExercise（标准动作库）
              │                                name / primary_muscles / secondary_muscles
              │                                equipment / level / instructions (JSONB)
              └── ExerciseSet             ← 某动作的一组数据
                    weight / reps / peak_hr / rest_hr / score
```

---

## 核心业务流程

### 1. 启动初始化（lifespan）

```
FastAPI 启动
  → 加载 .env
  → 初始化 HeartRateSyncService（心率服务单例，挂载到 app.state）
  → 初始化 LGFitnessAgent（LLM Agent 单例，挂载到 app.state）
  → create_db_and_tables()（自动建表）
  → AsyncPostgresSaver.setup()（自动建 checkpoint 相关表）
```

### 2. 用户登录 / 注册

```
LoginScreen → GET /user/{session_id}
  ├── 已存在 → 直接进入训练计划页
  └── 不存在 → RegisterCard → POST /user/create

注：session_id 直接复用 HypeRate 设备 ID，一物两用
```

### 3. 创建训练计划 & 选择动作

```
PlanSetupScreen → POST /exercise/create_plan
  → 返回 plan_id（后续全程使用，也作为 LangGraph thread_id）

MuscleSelectScreen → GET /exercise/muscles_list
  → PostgreSQL jsonb_array_elements_text 展开 JSONB 数组去重

ExerciseSelectScreen → GET /exercise/exercise_list?muscle=xxx
  → BaseExercise JSONB contains 查询
  → POST /exercise/add_exercises（写入 PlanExercise 表，返回 exercise_id）
```

### 4. 训练中 —— 每组核心流程

```
用户开始做这组
  → POST /sync/resume_polling
      → can_run.set()（绿灯，开始每 2s 采集 HypeRate 心率）

用户完成这组，点击「完成」
  → POST /sync/pause_polling { exercise_id, weight, reps }
      │
      ├─ 1. can_run.clear()（红灯，停止采集）
      │
      ├─ 2. FatigueAnalyzer 计算疲劳评分（0~100，越高越疲劳）
      │       peak_hr  = max(current_sample[].hr)
      │       rest_hr  = last_value（当前采集到的最新心率）
      │
      │       rec_score（0~70）：心率恢复率 HRR = (peak - rest) / peak
      │           HRR >= 18% → 10分（恢复优秀）
      │           HRR >= 12% → 40分（恢复良好）
      │           HRR <  12% → 70分（恢复差）
      │
      │       hist_score（0~30）：HR效率 = peak_hr / (%1RM)
      │           与该动作历史均值对比，超出 30% → 附加 30分
      │
      │       total_score = rec_score + hist_score
      │
      ├─ 3. SetsService.create_set() → 写入 ExerciseSet 表
      │
      └─ 4. LGFitnessAgent.lg_run_analysis()
              ├── 从 PostgreSQL checkpoint 读取同 plan_id 的历史消息
              ├── 首组：注入 SystemMessage(ANALYSIS_SYSTEM_PROMPT) + HumanMessage
              │   后续组：仅追加 HumanMessage（利用跨组记忆）
              ├── ReAct 推理循环（工具按需调用）：
              │     calculate_1rm(weight, reps)          → Epley 公式估算 1RM
              │     get_exercise_history(exercise_id)    → 历史组数数据
              │     get_plan_history(limit)              → 历史训练计划列表
              │     get_sets_detail_by_plan_id(plan_id)  → 计划内详细组数数据
              │     search_exercise_knowledge(query)     → RAG 双库检索
              │           exercises 库：exercise.json，MMR k=10
              │           champion_book 库：世界冠军健身全书 MD，MultiQuery k=5
              └── 返回结构化分析文字（强度/疲劳/历史对比/下组建议）
```

### 5. AI 对话教练

```
POST /chat/ai_chat { session_id, message }
  → LGFitnessAgent.lg_chat()
  → thread_id = "chat_{session_id}"（与训练记忆隔离）
  → 同一套 ReAct 工具，侧重自然语言问答
  → SystemMessage 使用 CHAT_SYSTEM_PROMPT
```

---

## RAG 知识库

| Collection | 数据源 | 处理方式 | 检索策略 |
|---|---|---|---|
| `exercises` | `db/exercise.json`（~860 条标准动作）| 每条转为自然语言文本，直接向量化入库 | MMR，k=10，fetch_k=30 |
| `champion_book` | 世界冠军健身全书（PDF → Markdown）| `MarkdownHeaderTextSplitter` 按标题分层，再 `RecursiveCharacterTextSplitter`（chunk=600, overlap=120）| MultiQueryRetriever（LLM 扩写查询）+ MMR，k=5 |

**PDF 离线解析**：运行 `llm/rag/ingest_pdf.py`，使用 `marker` 库（支持 GPU/CUDA）将 PDF 转为 Markdown，存入 `data/document/`，首次启动时自动入库。

---

## LangGraph ReAct 图结构

```
START
  │
  ▼
[agent]  ← call_model(state, config)
  │        llm 通过 config["configurable"]["llm"] 注入（解耦模型与图）
  │
  ├── 有 tool_calls ──→ [action] ToolNode
  │                          │  执行对应工具函数
  │                          └──→ 回到 [agent]
  │
  └── 无 tool_calls ──→ END

checkpointer = AsyncPostgresSaver
  → 每次 ainvoke 自动将消息历史持久化到 PostgreSQL
  → 训练分析：thread_id = str(plan_id)（同一计划跨组共享记忆）
  → 对话教练：thread_id = "chat_{session_id}"（独立会话）
```

---

## API 路由总览

### 心率同步 `/sync`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/sync/create_polling` | 启动心率轮询（后台任务）|
| POST | `/sync/pause_polling` | 完成一组，停止采集，触发疲劳计算 + AI 分析 |
| POST | `/sync/resume_polling?session_id=xxx` | 休息结束，恢复心率监测 |
| GET | `/sync/current_hr` | 获取当前心率（服务缓存值）|
| GET | `/sync/new_current_hr` | 通过 session_id 直接请求 HypeRate |

### 用户 `/user`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/user/create` | 注册用户（session_id / 姓名 / 年龄 / 身高 / 体重）|
| GET | `/user/{session_id}` | 查询用户信息 |

### 动作与计划 `/exercise`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/exercise/muscles_list` | 获取所有肌肉部位列表（JSONB 展开去重）|
| GET | `/exercise/exercise_list?muscle=xxx` | 按肌肉部位筛选标准动作 |
| POST | `/exercise/create_plan` | 创建训练计划 |
| POST | `/exercise/add_exercises` | 向计划添加动作 |
| POST | `/exercise/add_sets` | 手动添加训练组记录 |

### AI 对话 `/chat`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/chat/ai_chat` | 与 AI 教练自由对话，支持查询历史训练 + 动作知识 |

---

## 快速启动

### 后端

```bash
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（根目录新建 .env）
```

```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/muscleguard

# LLM（任意 OpenAI 兼容接口）
LLM_MODEL_ID=your-model-id
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-llm-endpoint
LLM_TIMEOUT=60
```

```bash
# 4. 初始化动作库（首次运行）
python db/init_script.py

# 5. 启动后端服务
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- 健康检查：`GET /health`
- Swagger 文档：`GET /docs`

### 前端

```bash
cd frontend
pnpm install
pnpm dev
# 访问 http://localhost:3000
```

> 如需手机访问，可使用 `ngrok http 3000` 暴露本地端口。

### RAG 知识库初始化（可选）

```bash
# 将 PDF 放入 data/document/ 后运行
python llm/rag/ingest_pdf.py
# 首次启动后端时，ChromaDB 会自动从 exercise.json 建立向量索引
```

---

## 前端页面流程

```
login
  ├── 已注册 ──→ plan-setup
  └── 未注册 ──→ register ──→ plan-setup
                                  │
                              muscle-select
                                  │
                              exercise-select（可多次添加动作）
                                  │
                              training（训练主界面）
                                  │
                              ←── 添加更多动作（返回 exercise-select）
```

---

## 疲劳评分算法说明

**总分 0–100，越高越疲劳。**

### 心率恢复率评分（rec_score，0–70）

基于组后 1 分钟心率恢复率（HRR%）：

```
HRR% = (峰值心率 - 当前心率) / 峰值心率

HRR% >= 18%  →  10 分（恢复优秀，低疲劳）
HRR% >= 12%  →  40 分（恢复良好，中疲劳）
HRR% <  12%  →  70 分（恢复较差，高疲劳）
```

### 历史心率效率对比评分（hist_score，0–30）

消除重量差异后，横向比较疲劳程度：

```
HR 效率 = 峰值心率 / (%1RM)     # 同等强度下心率越高说明越疲劳
1RM 估算 = weight × (1 + reps / 30)   # Epley 公式

当前 HR 效率比历史均值高出 >= 30%  →  附加满分 30 分
线性插值，最低 0 分
```

---

## 开发进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| Day 1 | FastAPI 骨架、PostgreSQL 异步 ORM、用户/计划/动作/组数 CRUD | ✅ 完成 |
| Day 2 | 疲劳评分算法（HRR + 历史心率效率对比）、HypeRate 心率轮询服务 | ✅ 完成 |
| Day 3 | LangGraph ReAct Agent、LLM Tool Calling、组间上下文记忆（checkpoint）| ✅ 完成 |
| Day 4 | RAG 双知识库（动作库 + 世界冠军健身全书）、MultiQuery 检索 | ✅ 完成 |
| Day 5 | Next.js 前端、完整页面状态机、API 对接 | ✅ 完成 |
| Day 6 | AI 对话教练入口（/chat）、对话记忆隔离 | ✅ 完成 |
| 规划中 | 根据历史训练记录 + 今日目标智能制定计划 | 📋 规划中 |
| 规划中 | HRV / 睡眠状态评估，训练前预判今日状态 | 📋 规划中 |
| 规划中 | 多用户并发心率采集隔离 | 📋 规划中 | 