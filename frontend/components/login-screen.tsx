"use client"

import { useState } from "react"
import { Shield, ArrowRight, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface LoginScreenProps {
  onLogin: (sessionId: string) => Promise<boolean>
  onNeedRegister: (sessionId: string) => void
}

export function LoginScreen({ onLogin, onNeedRegister }: LoginScreenProps) {
  const [sessionId, setSessionId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sessionId.trim()) {
      setError("请输入 Session ID")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const exists = await onLogin(sessionId.trim())
      if (!exists) {
        onNeedRegister(sessionId.trim())
      }
    } catch {
      setError("连接失败，请重试")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      {/* Logo */}
      <div className="mb-8 flex flex-col items-center">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center mb-4 shadow-lg shadow-primary/20">
          <Shield className="w-10 h-10 text-primary-foreground" />
        </div>
        <h1 className="text-3xl font-bold text-foreground tracking-tight">MuscleGuard</h1>
        <p className="text-muted-foreground text-sm mt-1">AI 实时健身监测</p>
      </div>

      {/* Login Card */}
      <Card className="w-full max-w-sm bg-card/80 backdrop-blur-sm border-border/50">
        <CardHeader className="text-center pb-4">
          <CardTitle className="text-xl">开始训练</CardTitle>
          <CardDescription>输入您的 Session ID 继续</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                type="text"
                placeholder="输入 Session ID"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="h-14 text-lg text-center font-mono bg-input border-border/50 focus:border-primary/50 rounded-xl"
                disabled={isLoading}
              />
              {error && (
                <p className="text-sm text-destructive text-center">{error}</p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-14 text-lg font-semibold bg-primary hover:bg-primary/90 rounded-xl"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  进入训练
                  <ArrowRight className="w-5 h-5 ml-2" />
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Footer */}
      <p className="mt-8 text-xs text-muted-foreground text-center">
        首次使用？输入新 ID 即可创建账户
      </p>
    </div>
  )
}
