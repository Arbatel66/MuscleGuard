"use client"

import { useState } from "react"
import { Dumbbell, ArrowRight, Loader2, History, Clock3, Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

interface PlanSetupScreenProps {
  userName: string
  sessionId: string
  onPlanCreated: (planId: number, planName: string) => void
  onOpenHistory: () => void
}

export function PlanSetupScreen({ userName, sessionId, onPlanCreated, onOpenHistory }: PlanSetupScreenProps) {
  const [planName, setPlanName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const quickPlans = ["胸部训练", "背部训练", "腿部训练", "肩部训练", "手臂训练", "全身训练"]

  const handleSubmit = async (name: string) => {
    const finalName = name.trim()
    if (!finalName) {
      setError("请输入训练计划名称")
      return
    }
    setIsLoading(true)
    setError("")
    try {
      const res = await fetch("/api/exercise/create_plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "ngrok-skip-browser-warning": "true",
        },
        body: JSON.stringify({
          plan_name: finalName,
          session_id: sessionId,
        }),
      })
      if (!res.ok) throw new Error("创建失败")
      const data = await res.json()
      onPlanCreated(data.plan_id, data.plan_name)
    } catch {
      setError("创建训练计划失败，请重试")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <div className="mb-6 flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center mb-4 shadow-lg shadow-primary/20">
          <Dumbbell className="w-8 h-8 text-primary-foreground" />
        </div>
        <h1 className="text-2xl font-bold text-foreground">今天练什么？</h1>
        <p className="text-muted-foreground text-sm mt-1">嘿 {userName}，选一个训练计划开始吧</p>
      </div>

      <button
        type="button"
        onClick={onOpenHistory}
        className="group mb-6 w-full max-w-sm overflow-hidden rounded-3xl border border-primary/30 bg-[linear-gradient(135deg,rgba(255,98,56,0.18),rgba(255,255,255,0.03))] p-4 text-left shadow-[0_16px_50px_rgba(255,98,56,0.14)] transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-[0_24px_70px_rgba(255,98,56,0.2)]"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/20 text-primary">
              <History className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-primary/90">
                <Clock3 className="h-3.5 w-3.5" />
                历史记录
              </div>
              <h2 className="mt-1 text-lg font-bold text-foreground">查看历史训练计划</h2>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">
                回看过去的 plan、动作明细，以及每一组的重量、次数、心率和疲劳分。
              </p>
            </div>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 text-primary transition-transform duration-200 group-hover:translate-x-0.5">
            <Sparkles className="h-4 w-4" />
          </div>
        </div>
      </button>

      <div className="w-full max-w-sm mb-6">
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3 text-center">快速选择</p>
        <div className="grid grid-cols-2 gap-2">
          {quickPlans.map((name) => (
            <button
              key={name}
              onClick={() => handleSubmit(name)}
              disabled={isLoading}
              className="h-12 px-4 rounded-xl bg-secondary/60 hover:bg-secondary border border-border/40 hover:border-primary/40 text-sm font-medium text-foreground transition-all duration-200 disabled:opacity-50"
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3 w-full max-w-sm mb-6">
        <div className="flex-1 h-px bg-border/50" />
        <span className="text-xs text-muted-foreground">或自定义</span>
        <div className="flex-1 h-px bg-border/50" />
      </div>

      <Card className="w-full max-w-sm bg-card/80 backdrop-blur-sm border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">自定义训练名</CardTitle>
          <CardDescription className="text-xs">输入你想要的训练计划名称</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="planName" className="text-sm text-muted-foreground">计划名称</Label>
              <Input
                id="planName"
                type="text"
                placeholder="例如：周一胸肩训练"
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSubmit(planName)}
                className="h-12 bg-input border-border/50 rounded-xl"
                disabled={isLoading}
              />
            </div>
            {error && <p className="text-sm text-destructive text-center">{error}</p>}
            <Button
              onClick={() => handleSubmit(planName)}
              disabled={isLoading || !planName.trim()}
              className="w-full h-12 bg-primary hover:bg-primary/90 rounded-xl font-semibold"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  创建计划
                  <ArrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
