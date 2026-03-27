"use client"

import { useEffect, useState } from "react"
import { ListChecks, Loader2, ChevronLeft, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ExerciseItem {
  id: string
  name: string
  category?: string
  muscles?: string[]
}

export interface SelectedExercise {
  baseId: string
  name: string
  exerciseId: number
}

interface ExerciseSelectScreenProps {
  planId: number
  muscle: string
  planName: string
  onExercisesReady: (exercises: SelectedExercise[]) => void
  onBack: () => void
}

export function ExerciseSelectScreen({
  planId,
  muscle,
  planName,
  onExercisesReady,
  onBack,
}: ExerciseSelectScreenProps) {
  const [exercises, setExercises] = useState<ExerciseItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [isAdding, setIsAdding] = useState(false)

  useEffect(() => {
    const fetchExercises = async () => {
      try {
        const res = await fetch(
          `/api/exercise/exercise_list?muscle=${encodeURIComponent(muscle)}`,
          { headers: { "ngrok-skip-browser-warning": "true" } }
        )
        if (!res.ok) throw new Error("获取失败")
        const data = await res.json()
        setExercises(Array.isArray(data) ? data : [])
      } catch {
        setError("获取动作列表失败")
      } finally {
        setIsLoading(false)
      }
    }
    fetchExercises()
  }, [muscle])

  const toggleExercise = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleConfirm = async () => {
    if (selected.size === 0) return
    setIsAdding(true)
    setError("")
    try {
      const results: SelectedExercise[] = []
      for (const baseId of selected) {
        const exercise = exercises.find((e) => e.id === baseId)
        if (!exercise) continue
        const res = await fetch("/api/exercise/add_exercises", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true",
          },
          body: JSON.stringify({
            plan_id: planId,
            exercise_base_id: baseId,
          }),
        })
        if (!res.ok) throw new Error(`添加 ${exercise.name} 失败`)
        const data = await res.json()
        results.push({ baseId, name: exercise.name, exerciseId: data.exercise_id })
      }
      onExercisesReady(results)
    } catch (err) {
      setError(err instanceof Error ? err.message : "添加动作失败")
    } finally {
      setIsAdding(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <button
          onClick={onBack}
          className="p-2 rounded-xl bg-secondary/60 hover:bg-secondary border border-border/40 transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-foreground" />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-foreground">选择动作</h1>
          <p className="text-xs text-muted-foreground">
            {planName} · <span className="capitalize">{muscle}</span>
          </p>
        </div>
        {selected.size > 0 && (
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
            <span className="text-sm font-bold text-primary">{selected.size}</span>
          </div>
        )}
      </div>

      {/* Icon */}
      <div className="flex justify-center my-4">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/30 to-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
          <ListChecks className="w-7 h-7 text-emerald-400" />
        </div>
      </div>

      {/* Selected tags */}
      {selected.size > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {[...selected].map((id) => {
            const ex = exercises.find((e) => e.id === id)
            return (
              <span
                key={id}
                className="flex items-center gap-1 px-3 py-1 rounded-full bg-primary/20 border border-primary/40 text-xs text-primary font-medium"
              >
                {ex?.name ?? id}
                <button onClick={() => toggleExercise(id)}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
        </div>
      )}

      {/* Exercise List */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">加载动作列表...</p>
          </div>
        ) : error && exercises.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-destructive text-sm">{error}</p>
          </div>
        ) : exercises.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-muted-foreground text-sm">该部位暂无动作数据</p>
          </div>
        ) : (
          exercises.map((ex) => {
            const isSelected = selected.has(ex.id)
            return (
              <button
                key={ex.id}
                onClick={() => toggleExercise(ex.id)}
                className={`w-full text-left px-4 py-3.5 rounded-2xl border transition-all duration-200 flex items-center justify-between gap-3 ${
                  isSelected
                    ? "bg-emerald-500/15 border-emerald-500/50 shadow-sm shadow-emerald-500/10"
                    : "bg-secondary/40 border-border/40 hover:bg-secondary hover:border-border/60"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate ${
                    isSelected ? "text-emerald-400" : "text-foreground"
                  }`}>
                    {ex.name}
                  </p>
                  {ex.category && (
                    <p className="text-xs text-muted-foreground mt-0.5 capitalize">{ex.category}</p>
                  )}
                </div>
                <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 transition-all ${
                  isSelected
                    ? "bg-emerald-500 border-emerald-500"
                    : "border-border/60 bg-transparent"
                }`}>
                  {isSelected && (
                    <svg viewBox="0 0 20 20" fill="white" className="w-full h-full">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              </button>
            )
          })
        )}
      </div>

      {/* Error (add phase) */}
      {error && exercises.length > 0 && (
        <p className="text-sm text-destructive text-center mt-2">{error}</p>
      )}

      {/* Confirm Button */}
      <div className="mt-4 pt-4 border-t border-border/30">
        <Button
          onClick={handleConfirm}
          disabled={selected.size === 0 || isAdding}
          className="w-full h-14 text-lg font-bold rounded-2xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-40"
        >
          {isAdding ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            `加入计划 (${selected.size} 个动作)`
          )}
        </Button>
      </div>
    </div>
  )
}
