"use client"

import { Trophy, CheckCircle2, TrendingUp, Calendar, Dumbbell, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface TrainingSummaryModalProps {
  summary: string
  planName?: string
  totalSets: number
  onClose: () => void
  onBackToHome: () => void
}

export function TrainingSummaryModal({ 
  summary, 
  planName, 
  totalSets, 
  onClose, 
  onBackToHome 
}: TrainingSummaryModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-card rounded-3xl border border-border/50 overflow-hidden animate-in fade-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="relative bg-gradient-to-br from-emerald-500/20 via-primary/20 to-blue-500/20 px-6 py-8 border-b border-border/30">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-xl bg-secondary/50 hover:bg-secondary transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
          
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/20 flex items-center justify-center">
              <Trophy className="w-8 h-8 text-emerald-400" />
            </div>
            <div className="text-center">
              <h2 className="text-2xl font-bold text-foreground">训练完成！</h2>
              <p className="text-sm text-muted-foreground mt-1">恭喜你完成今天的训练计划</p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center justify-center gap-6 mt-6">
            <div className="flex flex-col items-center">
              <div className="flex items-center gap-1.5 mb-1">
                <Dumbbell className="w-4 h-4 text-primary" />
                <span className="text-xs text-muted-foreground">完成组数</span>
              </div>
              <span className="text-2xl font-bold text-foreground tabular-nums">{totalSets}</span>
            </div>
            {planName && (
              <div className="flex flex-col items-center">
                <div className="flex items-center gap-1.5 mb-1">
                  <Calendar className="w-4 h-4 text-blue-400" />
                  <span className="text-xs text-muted-foreground">训练计划</span>
                </div>
                <span className="text-sm font-semibold text-foreground truncate max-w-[120px]">{planName}</span>
              </div>
            )}
          </div>
        </div>

        {/* AI Summary */}
        <div className="px-6 py-6 space-y-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/20">
              <TrendingUp className="w-4 h-4 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">AI 训练总结</span>
          </div>

          <div className="bg-secondary/40 rounded-2xl border border-border/30 p-4">
            <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">
              {summary || "正在生成训练总结..."}
            </p>
          </div>

          <div className="flex items-start gap-2 px-4 py-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-emerald-400">训练数据已保存</p>
              <p className="text-xs text-muted-foreground mt-0.5">你可以在历史记录中查看详细数据</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 pb-6 space-y-3">
          <Button
            onClick={onBackToHome}
            className="w-full h-12 text-base font-bold rounded-2xl bg-primary hover:bg-primary/90"
          >
            返回主页
          </Button>
          <Button
            onClick={onClose}
            variant="outline"
            className="w-full h-12 text-base font-medium rounded-2xl"
          >
            继续训练
          </Button>
        </div>
      </div>
    </div>
  )
}
