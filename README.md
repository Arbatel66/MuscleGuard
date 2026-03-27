# MuscleGuard（原型后端）

第一阶段目标：接收 Apple Watch 同步到 iPhone 的实时心率点，结合“训练组（动作/重量/次数）”计算疲劳度（基于 60 秒心率恢复速度 + 个人历史同重量纵向对比），并返回下一组建议。

## 运行

在项目根目录：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

启动后默认监听 `0.0.0.0:8000`，健康检查：

- `GET /health`

Swagger 文档：

- `GET /docs`

## API（原型）

### 1) 开始一组训练

`POST /training/start`

示例 body：

```json
{
  "user_id": "default",
  "exercise": "bench_press",
  "weight": 80
}
```

返回里会给你 `set_id`，后续心率上报建议带上它。

### 2) 上报心率点（实时）

`POST /training/heartrate`

```json
{
  "user_id": "default",
  "set_id": "default-1700000000000",
  "bpm": 132,
  "timestamp": "2026-03-06T12:34:56Z"
}
```

如果不传 `set_id`，服务会尝试把心率点绑定到最近的 active 训练组（原型方便用）。

### 3) 结束一组训练并获取建议

`POST /training/finish`

```json
{
  "user_id": "default",
  "set_id": "default-1700000000000",
  "reps": 5
}
```

返回：

```json
{
  "advice": "...",
  "fatigue_score": 62
}
```

## 数据存储

SQLite 文件默认在 `data/muscleguard.db`。

