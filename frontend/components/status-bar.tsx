"use client"

import { User, Weight, Hash } from "lucide-react"

interface StatusBarProps {
  name: string
  weight: number
  sessionId: string
}

export function StatusBar({ name, weight, sessionId }: StatusBarProps) {
  return (
    <div className="flex items-center justify-between w-full px-4 py-3 bg-secondary/30 backdrop-blur-sm rounded-2xl border border-border/30">
      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-primary/20">
          <User className="w-4 h-4 text-primary" />
        </div>
        <span className="text-sm font-medium text-foreground">{name}</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-emerald-500/20">
          <Weight className="w-4 h-4 text-emerald-400" />
        </div>
        <span className="text-sm font-medium text-foreground">{weight} kg</span>
      </div>

      <div className="flex items-center gap-2">
        <div className="p-1.5 rounded-lg bg-blue-500/20">
          <Hash className="w-4 h-4 text-blue-400" />
        </div>
        <span className="text-xs font-mono text-muted-foreground">{sessionId}</span>
      </div>
    </div>
  )
}
