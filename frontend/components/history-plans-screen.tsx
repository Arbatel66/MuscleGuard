"use client"

import { useMemo, useState } from "react"
import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, Dumbbell, HeartPulse, Layers3, ListOrdered, Loader2, Weight, Sparkles } from "lucide-react"
import { StatusBar } from "@/components/status-bar"
import { Button } from "@/components/ui/button"

type HistorySet = { set_id: number; weight: number; reps: number; peak_hr?: number | null; rest_hr?: number | null; score?: number | null }
type HistoryExercise = { plan_id: number; exercise_id: number; exercise_base_id: string; exercise_name: string; sets: HistorySet[] }
type HistoryPlan = { plan_name: string; plan_id: number; session_id: string; start_time: string; exercises: HistoryExercise[]; training_summary?: string | null }
type UserData = { name: string; weight: number; sessionId: string }

interface Props {
  userData: UserData
  plans: HistoryPlan[]
  loading: boolean
  error: string
  onBack: () => void
  onRefresh: () => Promise<void>
}

const fmtDate = (v: string) => {
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? v : new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(d)
}

const scoreColor = (score?: number | null) => {
  if (score == null) return "text-muted-foreground"
  if (score < 40) return "text-emerald-400"
  if (score < 70) return "text-yellow-400"
  if (score < 85) return "text-orange-400"
  return "text-red-400"
}

export function HistoryPlansScreen({ userData, plans, loading, error, onBack, onRefresh }: Props) {
  const [openPlan, setOpenPlan] = useState<number | null>(null)
  const [openExercises, setOpenExercises] = useState<Record<number, boolean>>({})

  const stats = useMemo(() => ({
    plans: plans.length,
    exercises: plans.reduce((a, p) => a + p.exercises.length, 0),
    sets: plans.reduce((a, p) => a + p.exercises.reduce((b, e) => b + e.sets.length, 0), 0),
  }), [plans])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(255,98,56,0.22),transparent_55%)]" />
        <div className="absolute -left-20 bottom-10 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col px-4 pb-10 pt-4 sm:px-6">
        <StatusBar name={userData.name} weight={userData.weight} sessionId={userData.sessionId} />

        <div className="mt-5 rounded-[28px] border border-border/40 bg-card/70 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.28)] backdrop-blur-xl sm:p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-primary">History Vault</p>
              <h1 className="mt-2 text-3xl font-bold">训练历史计划</h1>
              <p className="mt-2 text-sm text-muted-foreground">先显示计划，再展开查看动作和每一组的详细数据。</p>
            </div>
            <Button variant="outline" onClick={onBack} className="rounded-2xl border-border/50 bg-secondary/35">
              <ChevronLeft className="h-4 w-4" />返回
            </Button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-border/40 bg-secondary/35 p-4"><div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><Layers3 className="h-4 w-4 text-primary" />计划</div><div className="text-3xl font-bold">{stats.plans}</div></div>
            <div className="rounded-2xl border border-border/40 bg-secondary/35 p-4"><div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><Dumbbell className="h-4 w-4 text-emerald-400" />动作</div><div className="text-3xl font-bold">{stats.exercises}</div></div>
            <div className="rounded-2xl border border-border/40 bg-secondary/35 p-4"><div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground"><ListOrdered className="h-4 w-4 text-blue-400" />组数</div><div className="text-3xl font-bold">{stats.sets}</div></div>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between">
          <h2 className="text-xl font-semibold">历史计划列表</h2>
          <Button variant="outline" onClick={() => void onRefresh()} className="rounded-2xl border-border/50 bg-secondary/35">刷新</Button>
        </div>

        {loading ? <div className="mt-8 flex min-h-[240px] flex-col items-center justify-center gap-3 rounded-[28px] border border-border/40 bg-card/60"><Loader2 className="h-8 w-8 animate-spin text-primary" /><p className="text-sm text-muted-foreground">正在加载历史计划...</p></div> : error ? <div className="mt-8 rounded-[28px] border border-destructive/30 bg-destructive/10 p-6 text-center"><p className="text-sm text-destructive">{error}</p></div> : plans.length === 0 ? <div className="mt-8 rounded-[28px] border border-border/40 bg-card/60 p-8 text-center"><CalendarDays className="mx-auto mb-3 h-8 w-8 text-muted-foreground" /><p className="text-sm text-muted-foreground">暂无历史计划</p></div> : <div className="mt-5 space-y-4">
          {plans.map((plan) => {
            const expanded = openPlan === plan.plan_id
            const setCount = plan.exercises.reduce((a, e) => a + e.sets.length, 0)
            return <div key={plan.plan_id} className="overflow-hidden rounded-[26px] border border-border/40 bg-card/70 shadow-[0_18px_60px_rgba(0,0,0,0.2)] backdrop-blur-xl">
              <button onClick={() => setOpenPlan(expanded ? null : plan.plan_id)} className="flex w-full items-center justify-between gap-4 p-5 text-left hover:bg-secondary/20">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground"><span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-primary">Plan #{plan.plan_id}</span><span>{fmtDate(plan.start_time)}</span></div>
                  <h3 className="mt-3 text-xl font-semibold">{plan.plan_name}</h3>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full bg-secondary/45 px-3 py-1.5">{plan.exercises.length} 个动作</span>
                    <span className="rounded-full bg-secondary/45 px-3 py-1.5">{setCount} 组训练</span>
                    {plan.training_summary && (
                      <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-1.5 text-emerald-400 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />有总结
                      </span>
                    )}
                  </div>
                </div>
                <div className="rounded-2xl border border-border/40 bg-secondary/35 p-2 text-muted-foreground">{expanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}</div>
              </button>

              {expanded && <div className="border-t border-border/30 px-4 pb-5 pt-4 sm:px-6 space-y-4">
                {plan.training_summary && (
                  <div className="rounded-2xl border border-primary/25 overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-3 bg-primary/10 border-b border-primary/15">
                      <div className="p-1 rounded-lg bg-primary/20">
                        <Sparkles className="w-4 h-4 text-primary" />
                      </div>
                      <span className="text-sm font-semibold text-foreground">AI 训练总结</span>
                    </div>
                    <div className="px-4 py-4">
                      <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">
                        {plan.training_summary}
                      </p>
                    </div>
                  </div>
                )}
                {plan.exercises.length === 0 ? <div className="rounded-2xl border border-dashed border-border/40 bg-secondary/20 px-4 py-6 text-center text-sm text-muted-foreground">这个计划还没有动作记录。</div> : <div className="space-y-3">{plan.exercises.map((exercise, i) => {
                const exOpen = openExercises[exercise.exercise_id] ?? true
                return <div key={exercise.exercise_id} className="overflow-hidden rounded-2xl border border-border/35 bg-secondary/25">
                  <button onClick={() => setOpenExercises((c) => ({ ...c, [exercise.exercise_id]: !exOpen }))} className="flex w-full items-center justify-between gap-4 px-4 py-4 text-left hover:bg-secondary/25">
                    <div>
                      <div className="flex items-center gap-2"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/15 text-sm font-bold text-primary">{i + 1}</div><div><p className="text-sm font-semibold">{exercise.exercise_name}</p><p className="text-xs text-muted-foreground">动作 {i + 1} · {exercise.exercise_base_id}</p></div></div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground"><span className="rounded-full bg-background/40 px-3 py-1.5">{exercise.sets.length} 组</span></div>
                    </div>
                    <div className="rounded-2xl border border-border/35 bg-background/25 p-2 text-muted-foreground">{exOpen ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}</div>
                  </button>

                  {exOpen && <div className="border-t border-border/25 px-3 pb-3 pt-3 sm:px-4">{exercise.sets.length === 0 ? <div className="rounded-xl border border-dashed border-border/35 bg-background/20 px-3 py-4 text-center text-sm text-muted-foreground">这个动作还没有组数记录。</div> : <div className="space-y-2">{exercise.sets.map((set, idx) => <div key={set.set_id} className="rounded-xl border border-border/30 bg-background/30 px-4 py-3"><div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><span className="rounded-full bg-primary/15 px-2.5 py-1 text-xs font-medium text-primary">第 {idx + 1} 组</span></div>{set.score != null && <div className={`text-sm font-semibold ${scoreColor(set.score)}`}>疲劳分 {set.score}</div>}</div><div className="mt-3 grid gap-2 sm:grid-cols-4"><div className="rounded-xl bg-secondary/35 px-3 py-2"><p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">次数</p><p className="mt-1 text-lg font-bold">{set.reps}</p></div><div className="rounded-xl bg-secondary/35 px-3 py-2"><p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">重量</p><p className="mt-1 text-lg font-bold">{set.weight}<span className="ml-1 text-xs text-muted-foreground">kg</span></p></div><div className="rounded-xl bg-secondary/35 px-3 py-2"><p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">峰值心率</p><p className="mt-1 text-lg font-bold">{set.peak_hr ?? "--"}<span className="ml-1 text-xs text-muted-foreground">BPM</span></p></div><div className="rounded-xl bg-secondary/35 px-3 py-2"><p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">恢复心率</p><p className="mt-1 text-lg font-bold">{set.rest_hr ?? "--"}<span className="ml-1 text-xs text-muted-foreground">BPM</span></p></div></div></div>)}</div>}</div>}
                </div>
              })}</div>}</div>}
            </div>
          })}
        </div>}
      </div>
    </div>
  )
}
