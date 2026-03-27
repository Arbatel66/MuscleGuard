"use client"

import { TrendingUp, Activity } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"

interface DataCardProps {
  label: string
  value: number | string
  unit?: string
  icon: "peak" | "score"
  trend?: "up" | "down" | "neutral"
}

export function DataCard({ label, value, unit, icon, trend = "neutral" }: DataCardProps) {
  return (
    <Card className="bg-secondary/50 border-border/50 backdrop-blur-sm">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-2">
          {icon === "peak" ? (
            <TrendingUp className="w-4 h-4 text-red-400" />
          ) : (
            <Activity className="w-4 h-4 text-emerald-400" />
          )}
          <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
            {label}
          </span>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold tabular-nums text-foreground">
            {value}
          </span>
          {unit && (
            <span className="text-sm text-muted-foreground">{unit}</span>
          )}
        </div>
        {trend !== "neutral" && (
          <div
            className={`mt-1 text-xs font-medium ${
              trend === "up" ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {trend === "up" ? "↑ 较上次提升" : "↓ 较上次下降"}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
