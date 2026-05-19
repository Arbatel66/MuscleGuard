<div style="font-size:11px; line-height:1.18; margin:0; padding:0;">

<h2 style="margin:0 0 4px 0; font-size:18px;">MuscleGuard 面试小抄｜四宫格单屏版</h2>
<p style="margin:0 0 6px 0;"><b>主线：</b>5天迭代｜三层架构｜三层记忆｜Saga一致性｜RAG召回率+30%</p>

<table style="width:100%; border-collapse:collapse; table-layout:fixed; margin:0;">
<tr>
<td style="width:50%; vertical-align:top; border:1px solid #999; padding:5px;">

<h3 style="margin:0 0 4px 0; font-size:14px;">① 从0到1：5天迭代</h3>

<table style="width:100%; border-collapse:collapse; font-size:10.5px; line-height:1.15;">
<tr><th>Day</th><th>主题</th><th>关键词</th></tr>
<tr><td>1</td><td>基础</td><td>FastAPI + PostgreSQL(asyncpg) + SQLModel；4表 User→Plan→Exercise→Set；HypeRate 2s轮询</td></tr>
<tr><td>2</td><td>评分</td><td>HRR：≥18%=10，≥12%=40，&lt;12%=70；历史效率 HR/(weight/1RM)，超30%加30</td></tr>
<tr><td>3</td><td>Agent</td><td>手动ReAct→LangGraph；Tools：1RM/历史/RAG；AsyncPostgresSaver，thread_id=plan_id</td></tr>
<tr><td>4</td><td>RAG</td><td>单库→双库 exercises+champion_book；余弦→MMR+MultiQuery；ChromaDB</td></tr>
<tr><td>5</td><td>记忆</td><td>L1滑窗6000 tokens；L2滚动总结；last_summarized_id游标</td></tr>
</table>

<p style="margin:4px 0 0 0;"><b>口诀：</b>基础 / 评分 / Agent / RAG / 记忆</p>

</td>
<td style="width:50%; vertical-align:top; border:1px solid #999; padding:5px;">

<h3 style="margin:0 0 4px 0; font-size:14px;">② 架构与通信</h3>

<p style="margin:0 0 3px 0;"><b>分层：</b>Controller → Service → Model → DB</p>

<pre style="font-size:10px; line-height:1.1; margin:3px 0; padding:3px;">POST /sync/resume_polling → HypeRate每2s采集
POST /sync/pause_polling  → 停止并触发：
  1 FatigueAnalyzer算分
  2 SetsService写DB
  3 LGFitnessAgent推理建议</pre>

<pre style="font-size:10px; line-height:1.1; margin:3px 0; padding:3px;">LangGraph:
START → agent → 有tool_calls?
        ├ 是 → action → agent
        └ 否 → END</pre>

<table style="width:100%; border-collapse:collapse; font-size:10.5px; line-height:1.15;">
<tr><td>前后端</td><td>REST JSON</td><td>心率</td><td>asyncio任务</td></tr>
<tr><td>Agent</td><td>函数调用</td><td>记忆</td><td>PG checkpoint</td></tr>
</table>

<p style="margin:4px 0 0 0;"><b>口诀：</b>分层架构 + ReAct图 + 异步轮询</p>

</td>
</tr>
<tr>
<td style="width:50%; vertical-align:top; border:1px solid #999; padding:5px;">

<h3 style="margin:0 0 4px 0; font-size:14px;">③ Memory三层架构</h3>

<table style="width:100%; border-collapse:collapse; font-size:10.5px; line-height:1.15;">
<tr><td><b>L0</b></td><td>Checkpoint完整历史，PostgreSQL持久化</td></tr>
<tr><td><b>L1</b></td><td>滑动窗口，保最近细节，约6000 tokens</td></tr>
<tr><td><b>L2</b></td><td>滚动总结，保长期目标/偏好/关键事实</td></tr>
</table>

<p style="margin:4px 0 2px 0;"><b>最难：</b>只总结“滑出窗口的新消息”。</p>
<p style="margin:0 0 2px 0;"><b>触发：</b>未总结≥24且滑出≥1000 tokens，或未总结总量≥5000 tokens。</p>

<pre style="font-size:10px; line-height:1.1; margin:3px 0; padding:3px;">实现：
1 trim_messages到2500找边界
2 last_summarized_id→边界抓滑出
3 LLM融合：旧总结+新滑出
4 更新last_summarized_id</pre>

<p style="margin:3px 0 0 0;"><b>原因：</b>纯滑窗丢早期；纯总结丢细节；组合兼顾长期+实时。</p>
<p style="margin:3px 0 0 0;"><b>口诀：</b>游标追踪 + 只总结滑出 + 融合生成</p>

</td>
<td style="width:50%; vertical-align:top; border:1px solid #999; padding:5px;">

<h3 style="margin:0 0 4px 0; font-size:14px;">④ 一致性 + 召回率</h3>

<p style="margin:0 0 2px 0;"><b>Saga问题：</b>create_task即发即弃，DB成功但Chroma失败会不一致。</p>
<pre style="font-size:10px; line-height:1.1; margin:3px 0; padding:3px;">写DB ✓ → 写Chroma ✗ → Checkpoint不更新
方案：每步成功注册补偿；失败逆序补偿</pre>
<p style="margin:0 0 4px 0;"><b>状态：</b>pending / completed / rolled_back；查询只返回 completed。</p>

<p style="margin:3px 0 2px 0;"><b>RAG召回率：</b>30个测试query，Recall=检索到相关数/总相关数</p>
<table style="width:100%; border-collapse:collapse; font-size:10.5px; line-height:1.15;">
<tr><td>单库+余弦</td><td>45%</td></tr>
<tr><td>双库+MMR+MultiQuery</td><td>58.5%</td></tr>
<tr><td>相对提升</td><td>30%</td></tr>
</table>
<p style="margin:3px 0 0 0;"><b>改进：</b>exercises动作库 + champion_book理论库；MMR提多样性；MultiQuery扩语义。</p>
<p style="margin:3px 0 0 0;"><b>口诀：</b>Saga保一致；双库MMR MultiQuery提召回</p>

</td>
</tr>
</table>

<p style="margin:5px 0 0 0;"><b>最终背诵：</b>5天构建；Controller-Service-Model；pause后评分落库Agent推理；Memory靠last_summarized_id只总结滑出；Saga补偿逆序回滚；RAG从45%到58.5%。</p>

</div>
