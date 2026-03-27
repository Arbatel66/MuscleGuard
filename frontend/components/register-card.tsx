"use client"

import { useState } from "react"
import { UserPlus, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"

interface RegisterCardProps {
  sessionId: string
  onRegister: (data: {
    sessionId: string
    name: string
    height: number
    weight: number
    age: number
  }) => Promise<void>
  onBack: () => void
}

export function RegisterCard({ sessionId, onRegister, onBack }: RegisterCardProps) {
  const [formData, setFormData] = useState({
    name: "",
    height: "",
    weight: "",
    age: "",
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name || !formData.height || !formData.weight || !formData.age) {
      setError("请填写所有字段")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      await onRegister({
        sessionId,
        name: formData.name,
        height: Number(formData.height),
        weight: Number(formData.weight),
        age: Number(formData.age),
      })
    } catch {
      setError("注册失败，请重试")
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <Card className="w-full max-w-sm bg-card/80 backdrop-blur-sm border-border/50">
        <CardHeader className="text-center pb-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mx-auto mb-3">
            <UserPlus className="w-6 h-6 text-emerald-400" />
          </div>
          <CardTitle className="text-xl">创建新账户</CardTitle>
          <CardDescription>
            Session ID: <span className="font-mono text-foreground">{sessionId}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm text-muted-foreground">
                姓名
              </Label>
              <Input
                id="name"
                type="text"
                placeholder="您的姓名"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="h-12 bg-input border-border/50 rounded-xl"
                disabled={isLoading}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="height" className="text-sm text-muted-foreground">
                  身高 (cm)
                </Label>
                <Input
                  id="height"
                  type="number"
                  placeholder="175"
                  value={formData.height}
                  onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                  className="h-12 bg-input border-border/50 rounded-xl"
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="weight" className="text-sm text-muted-foreground">
                  体重 (kg)
                </Label>
                <Input
                  id="weight"
                  type="number"
                  placeholder="70"
                  value={formData.weight}
                  onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
                  className="h-12 bg-input border-border/50 rounded-xl"
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="age" className="text-sm text-muted-foreground">
                年龄
              </Label>
              <Input
                id="age"
                type="number"
                placeholder="25"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                className="h-12 bg-input border-border/50 rounded-xl"
                disabled={isLoading}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={onBack}
                disabled={isLoading}
                className="flex-1 h-12 rounded-xl border-border/50"
              >
                返回
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex-1 h-12 bg-emerald-500 hover:bg-emerald-600 rounded-xl"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  "开始训练"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
