"use client"

import { useEffect, useState } from "react"
import { Target, Loader2, ArrowRight, ChevronLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

const MUSCLE_EMOJI: Record<string, string> = {
  chest: "💪",
  back: "🔙",
  legs: "🦵",
  shoulders: "🏋️",
  biceps: "💪",
  triceps: "💪",
  abs: "⚡",
  glutes: "🍑",
  hamstrings: "🦵",
  quadriceps: "🦵",
  calves: "🦵",
  forearms: "💪",
  traps: "🔙",
  lats: "🔙",
}

function getMuscleEmoji(muscle: string): string {
  const key = muscle.toLowerCase().replace(/\s+/g, "")
  for (const [k, v] of Object.entries(MUSCLE_EMOJI)) {
    if (key.includes(k)) return v
  }
  return "🏃"
}

interface MuscleSelectScreenProps {
  planName: string
  onMuscleSelected: (muscle: string) => void
  onBack: () => void
}

export function MuscleSelectScreen({ planName, onMuscleSelected, onBack }: MuscleSelectScreenProps) {
  const [muscles, setMuscles] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    const fetchMuscles = async () => {
      try {
        const res = await fetch("/api/exercise/muscles_list", {
          headers: { "ngrok-skip-browser-warning": "true" },
        })
        if (!res.ok) throw new Error("获取失败")
        const data: string[] = await res.json()
        setMuscles(data)
      } catch {
        setError("获取部位列表失败")
      } finally {
        setIsLoading(false)
      }
    }
    fetchMuscles()
  }, [])

  const handleConfirm = () => {
    if (selected) onMuscleSelected(selected)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={onBack}
          className="p-2 rounded-xl bg-secondary/60 hover:bg-secondary border border-border/40 transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-foreground" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-foreground">选择训练部位</h1>
          <p className="text-xs text-muted-foreground">{planName}</p>
        </div>
      </div>

      {/* Icon */}
      <div className="flex justify-center mb-6">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-orange-500/30 to-orange-500/10 border border-orange-500/20 flex items-center justify-center">
          <Target className="w-7 h-7 text-orange-400" />
        </div>
      </div>

      {/* Muscle Grid */}
      <div className="flex-1">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <p className="text-sm text-muted-foreground">加载部位列表...</p>
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <p className="text-destructive text-sm">{error}</p>
            <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
              重试
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {muscles.map((muscle) => (
              <button
                key={muscle}
                onClick={() => setSelected(muscle)}
                className={`h-16 px-4 rounded-2xl border text-sm font-medium transition-all duration-200 flex items-center gap-3 ${
                  selected === muscle
                    ? "bg-primary/20 border-primary/60 text-primary shadow-lg shadow-primary/10"
                    : "bg-secondary/40 border-border/40 text-foreground hover:bg-secondary hover:border-border/60"
                }`}
              >
                <span className="text-xl">{getMuscleEmoji(muscle)}</span>
                <span className="capitalize text-left leading-tight">{muscle}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Confirm Button */}
      <div className="mt-6 pt-4 border-t border-border/30">
        <Button
          onClick={handleConfirm}
          disabled={!selected}
          className="w-full h-14 text-lg font-bold rounded-2xl bg-primary hover:bg-primary/90 disabled:opacity-40"
        >
          <span>查看{selected ? ` ${selected} ` : ""}动作</span>
          <ArrowRight className="w-5 h-5 ml-2" />
        </Button>
      </div>
    </div>
  )
}
