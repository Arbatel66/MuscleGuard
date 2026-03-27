# MuscleGuard — AI 健身教练后端

> **当前进度：Day 3 / Memory 模块集成中**

基于 Apple Watch 实时心率数据，结合 LangGraph ReAct Agent，在每组训练结束后自动分析疲劳状态并给出下一组建议。

---

## 项目架构

```
MuscleGuard/
├── main.py                  # FastAPI 入口，注册路由，CORS 配置
├── lifespan.py              # 启动/关闭钩子：初始化 DB、HeartRateSyncService
├── requirements.txt
│
├── controller/              # 路由层（接收 HTTP 请求）
│   ├── sync.py              # 心率同步 & 组后分析（核心入口）
│   ├── user.py              # 用户注册/查询
│   └── exercise.py          # 计划/动作/组数 CRUD
│
├── services/                # 业务逻辑层
│   ├── fatigue_service.py   # 疲劳评分算法（HRR + 历史对比）
│   ├── sync_service.py      # Apple Watch 心率实时轮询
│   ├── plan_service.py      # 训练计划管理
│   ├── exercise_service.py  # 动作库查询
│   ├── sets_service.py      # 训练组 CRUD
│   └── user_service.py      # 用户信息 & 上下文生成
│
├── llm/
│   ├── prompt.py            # System Prompt（运动生理学 AI 教练人设）
│   ├── llm_client.py        # LLM 客户端封装
│   └── langGraph/
│       ├── lg_agent.py      # LangGraph ReAct Agent（核心 AI 逻辑）
│       └── lg_tools.py      # Agent 工具：1RM 计算、历史数据查询
│
├── models/                  # SQLModel 数据模型（对应 DB 表）
│   ├── User.py              # User
│   └── Plan_Exercise_Model.py  # WorkoutPlan / PlanExercise / ExerciseSet / BaseExercise
│
├── schemas/                 # Pydantic 请求/响应 Schema
│   ├── Workout_schemas.py
│   └── SessionManager.py
│
├── repositories/
│   └── workout_repository.py
│
├── db/
│   ├── database.py          # AsyncSession 工厂，建表
│   ├── init_script.py       # 从 exercise.json 初始化动作库
│   └── exercise.json        # 动作种子数据
│
├── data/
│   └── muscleguard.db       # SQLite 数据文件
│
└── free-exercise-db/        # 开源动作数据集（子模块）
```

---

## 核心功能

### 1. 实时心率采集

Apple Watch → iPhone → 后端轮询接口，每组训练期间持续采集心率序列。

- `POST /sync/create_polling` — 开始一组，启动心率采集
- `POST /sync/pause_polling` — 完成一组，停止采集并触发分析
- `POST /sync/resume_polling` — 进入休息期，恢复心率监测
- `GET  /sync/current_hr` — 查询当前实时心率

### 2. 疲劳评分算法（`fatigue_service.py`）

每组结束后自动计算 **0–100 分**（越高越疲劳）：

| 维度 | 满分 | 逻辑 |
|---|---|---|
| **心率恢复率（HRR）** | 70 | 一分钟心率恢复率 < 12% → 70分；>= 18% → 10分 |
| **历史心率效率对比** | 30 | 当前组 HR效率 比历史均值高出 ≥ 30% → 满分 30 |

> HR效率 = 峰值心率 / (%1RM)，消除重量差异后横向对比。

### 3. LangGraph ReAct Agent（`llm/langGraph/`）

疲劳评分完成后，自动调用 AI 教练进行分析：

```
HumanMessage（生理指标 + 用户信息 + 本组数据）
    ↓
[agent] LLM 推理
    ↓ 需要工具？
[action] ToolNode
    ├── calculate_1rm(weight, reps)         # Epley 公式计算理论最大力量
    └── get_exercise_history(exercise_id)   # 查询该动作历史数据
    ↓
[agent] LLM 综合输出
    ↓
返回：强度分析 / 疲劳表现 / 行动建议
```

**System Prompt 能力**：心率区间判断（Karvonen 公式）、HRR 评估、过度疲劳预警、数据驱动中文建议。

### 4. 数据模型层级

```
User (session_id)
 └── WorkoutPlan (训练计划)
      └── PlanExercise (动作，关联 BaseExercise 标准库)
           └── ExerciseSet (每一组：重量/次数/峰值心率/休息心率/疲劳分)

BaseExercise (free-exercise-db 导入的标准动作库，含肌肉群/器械/难度)
```

---

## API 路由总览

### 心率同步 `/sync`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/sync/create_polling` | 开始轮询心率 |
| POST | `/sync/pause_polling` | 完成一组，触发疲劳分析 + AI 建议 |
| POST | `/sync/resume_polling` | 休息结束，恢复心率监测 |
| GET | `/sync/current_hr` | 获取当前心率 |
| GET | `/sync/new_current_hr` | 通过 session_id 获取心率 |

### 用户 `/user`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/user/create` | 注册用户（session_id/姓名/年龄/身高/体重）|
| GET | `/user/{session_id}` | 查询用户信息 |

### 动作与计划 `/exercise`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/exercise/muscles_list` | 获取所有肌肉部位列表 |
| GET | `/exercise/exercise_list` | 按肌肉部位筛选动作 |
| POST | `/exercise/create_plan` | 创建训练计划 |
| POST | `/exercise/add_exercises` | 向计划添加动作 |
| POST | `/exercise/add_sets` | 手动添加训练组记录 |

---

## 快速启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量（复制后填入你的 LLM Key）
copy db\.env.example db\.env

# 启动服务
python main.py
```

服务默认监听 `0.0.0.0:8000`

- 健康检查：`GET /health`
- Swagger 文档：`GET /docs`

### 环境变量（`db/.env`）

```env
LLM_MODEL_ID=your-model-id
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-llm-endpoint
```

---

## 开发进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| Day 1 | FastAPI 骨架、SQLite DB、用户/计划/动作/组数 CRUD、心率轮询服务 | ✅ 完成 |
| Day 2 | 疲劳评分算法（HRR + 历史对比）、LangGraph ReAct Agent、LLM Tool Calling | ✅ 完成 |
| Day 3 | Memory 模块：LangGraph Checkpointer，组间上下文保持 | 🔄 进行中 |
| 后续 | HRV / 睡眠状态评估、训练前状态预判、根据历史动作智能制定计划、前端 | 📋 规划中 |

---

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | SQLite（SQLAlchemy 异步）+ SQLModel ORM |
| AI 框架 | LangGraph + LangChain + OpenAI Compatible API |
| 心率采集 | Apple Watch → iPhone → 自研轮询服务 |
| 数据验证 | Pydantic v2 |
| 运行环境 | Python 3.12 |
