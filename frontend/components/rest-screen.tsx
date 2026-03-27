"use client"

import { useEffect, useState } from "react"
import { Coffee, Heart } from "lucide-react"

interface RestScreenProps {
  currentHr: number
  onComplete: (avgRestingHr: number) => void
}

export function RestScreen({ currentHr, onComplete }: RestScreenProps) {
  const [countdown, setCountdown] = useState(60)
  const [restingHrs, setRestingHrs] = useState<number[]>([])

  useEffect(() => {
    // Record resting heart rates (only if valid)
    if (currentHr > 0) {
      setRestingHrs((prev) => [...prev, currentHr])
    }
  }, [currentHr])

  useEffect(() => {
    if (countdown <= 0) {
      // Calculate average and pass to parent
      const avg = restingHrs.length > 0
        ? Math.round(restingHrs.reduce((a, b) => a + b, 0) / restingHrs.length)
        : currentHr
      onComplete(avg)
      return
    }

    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1)
    }, 1000)

    return () => clearInterval(timer)
  }, [countdown, onComplete, restingHrs, currentHr])

  const progress = ((60 - countdown) / 60) * 100
  const avgRestingHr = restingHrs.length > 0
    ? Math.round(restingHrs.reduce((a, b) => a + b, 0) / restingHrs.length)
    : currentHr

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      {/* Rest icon */}
      <div className="mb-8">
        <div className="w-24 h-24 rounded-full bg-blue-500/20 flex items-center justify-center">
          <Coffee className="w-12 h-12 text-blue-400" />
        </div>
      </div>

      {/* Message */}
      <h2 className="text-2xl font-bold text-foreground mb-2">休息一下吧</h2>
      <p className="text-muted-foreground mb-8">正在记录静息心率...</p>

      {/* Countdown ring */}
      <div className="relative w-48 h-48 mb-8">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="6"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="#3b82f6"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 45}
            strokeDashoffset={2 * Math.PI * 45 * (1 - progress / 100)}
            className="transition-all duration-1000 ease-linear"
            style={{
              filter: "drop-shadow(0 0 10px rgba(59, 130, 246, 0.5))",
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-5xl font-bold tabular-nums text-foreground">
            {countdown}
          </span>
          <span className="text-sm text-muted-foreground">秒</span>
        </div>
      </div>

      {/* Current resting HR */}
      <div className="flex items-center gap-3 px-6 py-4 bg-secondary/50 rounded-2xl border border-border/30">
        <Heart className="w-6 h-6 text-blue-400" />
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider">平均静息心率</p>
          <p className="text-2xl font-bold text-foreground tabular-nums">
            {avgRestingHr} <span className="text-sm font-normal text-muted-foreground">BPM</span>
          </p>
        </div>
      </div>
    </div>
  )
}
