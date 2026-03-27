"use client"

import { Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface AIAdviceCardProps {
  analysis: string
  isLoading?: boolean
}

export function AIAdviceCard({ analysis, isLoading = false }: AIAdviceCardProps) {
  return (
    <Card className="bg-gradient-to-br from-secondary/80 to-secondary/40 border-border/50 backdrop-blur-sm overflow-hidden">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <div className="p-1.5 rounded-lg bg-primary/20">
            <Sparkles className="w-4 h-4 text-primary" />
          </div>
          <span className="text-foreground">AI 训练建议</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-3 bg-muted/50 rounded animate-pulse w-full" />
            <div className="h-3 bg-muted/50 rounded animate-pulse w-4/5" />
            <div className="h-3 bg-muted/50 rounded animate-pulse w-3/5" />
          </div>
        ) : (
          <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {analysis || "开始训练后，AI 将实时分析您的心率数据并提供专业建议。"}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
