"use client"

import { useMemo } from "react"
import { Heart } from "lucide-react"

interface HeartRateRingProps {
  bpm: number
  maxHr?: number
  isActive?: boolean
}

type HRZone = "warmup" | "fatburn" | "cardio" | "peak"

function getHRZone(bpm: number, maxHr: number): HRZone {
  const percentage = (bpm / maxHr) * 100
  if (percentage < 60) return "warmup"
  if (percentage < 70) return "fatburn"
  if (percentage < 85) return "cardio"
  return "peak"
}

const zoneColors: Record<HRZone, { ring: string; glow: string; text: string; label: string }> = {
  warmup: {
    ring: "#4ade80",
    glow: "0 0 60px rgba(74, 222, 128, 0.5)",
    text: "text-green-400",
    label: "热身区",
  },
  fatburn: {
    ring: "#facc15",
    glow: "0 0 60px rgba(250, 204, 21, 0.5)",
    text: "text-yellow-400",
    label: "燃脂区",
  },
  cardio: {
    ring: "#fb923c",
    glow: "0 0 60px rgba(251, 146, 60, 0.5)",
    text: "text-orange-400",
    label: "有氧区",
  },
  peak: {
    ring: "#ef4444",
    glow: "0 0 60px rgba(239, 68, 68, 0.6)",
    text: "text-red-500",
    label: "极限区",
  },
}

export function HeartRateRing({ bpm, maxHr = 190, isActive = false }: HeartRateRingProps) {
  const zone = useMemo(() => getHRZone(bpm, maxHr), [bpm, maxHr])
  const zoneStyle = zoneColors[zone]
  const progress = Math.min((bpm / maxHr) * 100, 100)

  const strokeDasharray = 2 * Math.PI * 120
  const strokeDashoffset = strokeDasharray - (progress / 100) * strokeDasharray

  return (
    <div className="relative flex items-center justify-center">
      {/* Outer glow effect */}
      <div
        className="absolute inset-0 rounded-full blur-3xl opacity-30 transition-all duration-500"
        style={{ backgroundColor: zoneStyle.ring }}
      />

      {/* SVG Ring */}
      <svg
        width="280"
        height="280"
        viewBox="0 0 280 280"
        className="transform -rotate-90 transition-all duration-300"
        style={{ filter: `drop-shadow(${zoneStyle.glow})` }}
      >
        {/* Background ring */}
        <circle
          cx="140"
          cy="140"
          r="120"
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="12"
        />
        {/* Progress ring */}
        <circle
          cx="140"
          cy="140"
          r="120"
          fill="none"
          stroke={zoneStyle.ring}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500 ease-out"
        />
        {/* Zone markers */}
        {[60, 70, 85, 100].map((percent, i) => {
          const angle = ((percent / 100) * 360 - 90) * (Math.PI / 180)
          const x = 140 + 120 * Math.cos(angle)
          const y = 140 + 120 * Math.sin(angle)
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="4"
              fill="rgba(255,255,255,0.3)"
            />
          )
        })}
      </svg>

      {/* Center content */}
      <div className="absolute flex flex-col items-center justify-center">
        {/* Heart icon with pulse animation */}
        <div className={`mb-2 ${isActive ? "animate-pulse" : ""}`}>
          <Heart
            className={`w-8 h-8 ${zoneStyle.text} fill-current transition-colors duration-300`}
          />
        </div>

        {/* BPM Display */}
        <div className="flex items-baseline gap-1">
          <span
            className={`text-7xl font-bold tabular-nums tracking-tight ${zoneStyle.text} transition-colors duration-300`}
          >
            {bpm}
          </span>
          <span className="text-lg text-muted-foreground font-medium">BPM</span>
        </div>

        {/* Zone label */}
        <div
          className={`mt-2 px-4 py-1 rounded-full text-sm font-medium transition-all duration-300`}
          style={{ backgroundColor: `${zoneStyle.ring}20`, color: zoneStyle.ring }}
        >
          {zoneStyle.label}
        </div>
      </div>
    </div>
  )
}
