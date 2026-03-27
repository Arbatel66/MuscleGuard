"use client"

import { Trophy, Heart, TrendingUp, Sparkles, Clock, Plus, ChevronRight } from "lucide-react"
import type { SelectedExercise } from "@/components/exercise-select-screen"

interface SummaryModalProps {
  data: {
    peakHr: number
    avgHr: number
    restingHr: number
    score: number
    duration: number
    analysis: string
    exerciseName?: string
  }
  exercises: SelectedExercise[]
  currentExIdx: number
  onContinue: (exIdx: number) => void
  onAddExercise: () => void
}

function ScoreRing({ score }: { score: number }) {
  const r = 36
  const circ = 2 * Math.PI * r
  const pct = Math.min(score, 100) / 100
  const color = score < 40 ? "#4ade80" : score < 70 ? "#facc15" : score < 85 ? "#fb923c" : "#ef4444"
  const label = score < 40 ? "状态良好" : score < 70 ? "轻度疲劳" : score < 85 ? "较为疲劳" : "高度疲劳"
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
          <circle cx="44" cy="44" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={circ * (1 - pct)}
            style={{ transition: "stroke-dashoffset 0.8s ease", filter: `drop-shadow(0 0 6px ${color}80)` }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold tabular-nums" style={{ color }}>{score}</span>
        </div>
      </div>
      <span className="text-xs font-medium" style={{ color }}>{label}</span>
    </div>
  )
}

export function SummaryModal({ data, exercises, currentExIdx, onContinue, onAddExercise }: SummaryModalProps) {
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs.toString().padStart(2, "0")}秒`
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      <div className="flex-shrink-0 bg-black/40 backdrop-blur-sm" style={{ height: "8dvh" }} />

      <div className="flex-1 bg-card border-t border-border/50 rounded-t-3xl overflow-y-auto">
        <div className="sticky top-0 bg-card/95 backdrop-blur-sm pt-3 pb-3 px-6 border-b border-border/20 z-10">
          <div className="w-10 h-1 bg-border rounded-full mx-auto mb-3" />
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-foreground">本组完成 🎉</h2>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Clock className="w-3 h-3 text-muted-foreground" />
                <p className="text-xs text-muted-foreground">{formatDuration(data.duration)}</p>
              </div>
            </div>
            <ScoreRing score={data.score} />
          </div>
        </div>

        <div className="px-6 pb-10 pt-4 space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {[{label:"峰值",val:data.peakHr,color:"text-red-400"},{label:"平均",val:data.avgHr,color:"text-orange-400"},{label:"静息",val:data.restingHr,color:"text-blue-400"}].map(({label,val,color})=>(
              <div key={label} className="flex flex-col items-center gap-1 bg-secondary/40 rounded-2xl border border-border/30 py-3 px-2">
                <Heart className={`w-4 h-4 ${color}`} />
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-lg font-bold tabular-nums text-foreground">{val}</p>
                <p className="text-xs text-muted-foreground">BPM</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-primary/25 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 bg-primary/10 border-b border-primary/15">
              <div className="p-1 rounded-lg bg-primary/20"><Sparkles className="w-4 h-4 text-primary" /></div>
              <span className="text-sm font-semibold text-foreground">AI 分析建议</span>
            </div>
            <div className="px-4 py-4">
              <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">{data.analysis || "暂无分析数据"}</p>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">接下来练什么？</p>

            <button
              onClick={() => onContinue(currentExIdx)}
              className="w-full flex items-center justify-between px-4 py-3.5 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 hover:bg-emerald-500/25 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-emerald-400">继续 {exercises[currentExIdx]?.name}</p>
                  <p className="text-xs text-muted-foreground">再做一组</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-emerald-400" />
            </button>

            {exercises.filter((_, i) => i !== currentExIdx).map((ex) => {
              const idx = exercises.indexOf(ex)
              return (
                <button
                  key={ex.exerciseId}
                  onClick={() => onContinue(idx)}
                  className="w-full flex items-center justify-between px-4 py-3.5 rounded-2xl bg-secondary/40 border border-border/40 hover:bg-secondary hover:border-border/60 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-xl bg-secondary/60 flex items-center justify-center">
                      <span className="text-xs font-bold text-muted-foreground">{idx+1}</span>
                    </div>
                    <p className="text-sm font-medium text-foreground">{ex.name}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </button>
              )
            })}

            <button
              onClick={onAddExercise}
              className="w-full flex items-center justify-between px-4 py-3.5 rounded-2xl bg-secondary/20 border border-dashed border-border/50 hover:bg-secondary/40 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Plus className="w-4 h-4 text-primary" />
                </div>
                <p className="text-sm font-medium text-primary">增加新动作</p>
              </div>
              <ChevronRight className="w-4 h-4 text-primary" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
