"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Play, Pause, ChevronLeft, ChevronRight, Loader2, Dumbbell, Coffee, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { StatusBar } from "@/components/status-bar"
import { HeartRateRing } from "@/components/heart-rate-ring"
import { DataCard } from "@/components/data-card"
import { AIAdviceCard } from "@/components/ai-advice-card"
import { SummaryModal } from "@/components/summary-modal"
import type { SelectedExercise } from "@/components/exercise-select-screen"

interface UserData { name: string; weight: number; sessionId: string; age: number }
interface SetRecord { setId: number; reps: number; weight: number; peakHr?: number; score?: number }
interface PausePollingParams {
  sessionId: string; exerciseId: number; reps: number; weight: number
}
interface TrainingScreenProps {
  userData: UserData
  exercises: SelectedExercise[]
  onFetchHeartRate: () => Promise<number>
  onResumePolling: (sessionId: string) => Promise<void>
  onPausePolling: (p: PausePollingParams) => Promise<{ set_id: number; score: number; peakHr: number; restHr: number; analysis: string }>
  onAddExercise: () => void
}

export function TrainingScreen({ userData, exercises, onFetchHeartRate, onResumePolling, onPausePolling, onAddExercise }: TrainingScreenProps) {
  const [currentExIdx, setCurrentExIdx] = useState(0)
  const [isActive, setIsActive] = useState(false)
  const [currentHr, setCurrentHr] = useState(72)
  const [peakHr, setPeakHr] = useState(0)
  const [score, setScore] = useState(0)
  const [analysis, setAnalysis] = useState("")
  const [heartRates, setHeartRates] = useState<number[]>([])
  const [duration, setDuration] = useState(0)
  const [setRecords, setSetRecords] = useState<SetRecord[]>([])
  const [showSetModal, setShowSetModal] = useState(false)
  const [restCountdown, setRestCountdown] = useState(0)
  const [restHrs, setRestHrs] = useState<number[]>([])
  const [setReps, setSetReps] = useState("")
  const [setWeight, setSetWeight] = useState("")
  const [isSavingSet, setIsSavingSet] = useState(false)
  const [setError, setSetError] = useState("")
  const [showSummary, setShowSummary] = useState(false)
  const [summaryData, setSummaryData] = useState<{ peakHr: number; avgHr: number; restingHr: number; score: number; duration: number; analysis: string } | null>(null)

  const restHrsRef = useRef<number[]>([])
  const avgRestHrRef = useRef(0)
  const savedDuration = useRef(0)
  const savedPeakHr = useRef(0)
  const savedHeartRates = useRef<number[]>([])
  const savedCurrentHr = useRef(72)
  const pendingSubmit = useRef(false)  // user filled form before countdown ended

  const currentExercise = exercises[currentExIdx]
  const maxHr = 220 - userData.age
  const isResting = restCountdown > 0

  useEffect(() => {
    if (!isActive && !isResting) return
    const interval = setInterval(async () => {
      try {
        const hr = await onFetchHeartRate()
        setCurrentHr(hr)
        savedCurrentHr.current = hr
        if (isActive && hr > 0) { setHeartRates((p) => [...p, hr]); if (hr > peakHr) setPeakHr(hr) }
        if (isResting && hr > 0) { setRestHrs((p) => { const next = [...p, hr]; restHrsRef.current = next; return next }) }
      } catch { /* silent */ }
    }, 1000)
    return () => clearInterval(interval)
  }, [isActive, isResting, onFetchHeartRate, peakHr])

  useEffect(() => {
    if (!isActive) return
    const interval = setInterval(() => setDuration((p) => p + 1), 1000)
    return () => clearInterval(interval)
  }, [isActive])

  useEffect(() => {
    if (restCountdown <= 0) return
    const t = setTimeout(() => {
      if (restCountdown === 1) {
        const hrs = restHrsRef.current
        const avg = hrs.length > 0 ? Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length) : savedCurrentHr.current
        avgRestHrRef.current = avg
      }
      setRestCountdown((p) => p - 1)
    }, 1000)
    return () => clearTimeout(t)
  }, [restCountdown])

  const handleStart = async () => { try { await onResumePolling(userData.sessionId) } catch { /* silent */ }; setIsActive(true) }

  const handlePause = () => {
    savedDuration.current = duration
    savedPeakHr.current = peakHr
    savedHeartRates.current = heartRates
    setIsActive(false)
    setRestHrs([])
    setRestCountdown(60)
    setShowSetModal(true)
  }

  const handleSaveSet = useCallback(async () => {
    if (!setReps || !setWeight) { setSetError("请填写次数和重量"); return }
    // If countdown still running, mark pending and wait
    if (restCountdown > 0) {
      pendingSubmit.current = true
      setSetError("")
      return
    }
    setIsSavingSet(true); setSetError("")
    try {
      const restHrValue = avgRestHrRef.current || savedCurrentHr.current
      // Call pause_polling with full context — backend returns peak_hr/rest_hr/score from actual data
      const result = await onPausePolling({
        sessionId: userData.sessionId,
        exerciseId: currentExercise.exerciseId,
        reps: Number(setReps),
        weight: Number(setWeight),
      })
      setScore(result.score); setAnalysis(result.analysis)
      const avgHr = savedHeartRates.current.length > 0
        ? Math.round(savedHeartRates.current.reduce((a, b) => a + b, 0) / savedHeartRates.current.length)
        : savedCurrentHr.current
      setSetRecords((p) => [...p, {
        setId: result.set_id,
        reps: Number(setReps),
        weight: Number(setWeight),
        peakHr: result.peakHr,
        score: result.score,
      }])
      setSummaryData({
        peakHr: result.peakHr,
        avgHr,
        restingHr: result.restHr,
        score: result.score,
        duration: savedDuration.current,
        analysis: result.analysis,
      })
      setShowSetModal(false); setRestCountdown(0); setShowSummary(true)
      setHeartRates([]); setPeakHr(0); setDuration(0); setSetReps(""); setSetWeight("")
      avgRestHrRef.current = 0
    } catch { setSetError("保存失败，请重试") }
    finally { setIsSavingSet(false) }
  }, [setReps, setWeight, restCountdown, onPausePolling, userData.sessionId, currentExercise])

  const handleContinue = useCallback((exIdx: number) => {
    setCurrentExIdx(exIdx)
    setShowSummary(false)
    setSummaryData(null)
  }, [])

  const fmt = (s: number) => `${Math.floor(s/60).toString().padStart(2,"0")}:${(s%60).toString().padStart(2,"0")}`
  const restProgress = ((60 - restCountdown) / 60) * 100
  const avgRestHrDisplay = restHrs.length > 0 ? Math.round(restHrs.reduce((a,b)=>a+b,0)/restHrs.length) : currentHr

  return (
    <div className="min-h-screen bg-background flex flex-col p-4 pb-8">
      <StatusBar name={userData.name} weight={userData.weight} sessionId={userData.sessionId} />

      {/* Exercise Switcher */}
      <div className="mt-4 flex items-center gap-2 bg-secondary/40 rounded-2xl border border-border/40 p-3">
        <button onClick={() => setCurrentExIdx((i) => Math.max(0, i-1))} disabled={currentExIdx===0} className="p-1.5 rounded-lg bg-secondary/60 disabled:opacity-30">
          <ChevronLeft className="w-4 h-4 text-foreground" />
        </button>
        <div className="flex-1 text-center">
          <div className="flex items-center justify-center gap-2">
            <Dumbbell className="w-4 h-4 text-primary" />
            <p className="text-sm font-semibold text-foreground truncate">{currentExercise?.name ?? "无动作"}</p>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{currentExIdx+1} / {exercises.length} 个动作{setRecords.length > 0 && ` · 已完成 ${setRecords.length} 组`}</p>
        </div>
        <button onClick={() => setCurrentExIdx((i) => Math.min(exercises.length-1, i+1))} disabled={currentExIdx===exercises.length-1} className="p-1.5 rounded-lg bg-secondary/60 disabled:opacity-30">
          <ChevronRight className="w-4 h-4 text-foreground" />
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center gap-5 py-4">
        {isActive && (
          <div className="text-center">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">训练时长</p>
            <p className="text-2xl font-mono font-bold text-foreground tabular-nums">{fmt(duration)}</p>
          </div>
        )}
        <HeartRateRing bpm={currentHr} maxHr={maxHr} isActive={isActive} />
        <div className="grid grid-cols-2 gap-4 w-full">
          <DataCard label="峰值心率" value={peakHr || "--"} unit="BPM" icon="peak" />
          <DataCard label="疲劳得分" value={score || "--"} unit="/ 100" icon="score" />
        </div>
        <AIAdviceCard analysis={analysis} />
      </div>

      {/* Control Button */}
      <Button
        onClick={isActive ? handlePause : handleStart}
        disabled={showSetModal}
        className={`w-full h-16 text-xl font-bold rounded-2xl transition-all duration-300 disabled:opacity-50 ${
          isActive ? "bg-orange-500 hover:bg-orange-600" : "bg-emerald-500 hover:bg-emerald-600"
        }`}
      >
        {isActive ? <><Pause className="w-6 h-6 mr-2" />完成这一组</> : <><Play className="w-6 h-6 mr-2" />开始这一组</>}
      </Button>

      {/* ── Rest + Input Modal (parallel) ── */}
      {showSetModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm flex flex-col z-50 p-4">
          {/* Rest countdown strip */}
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            {restCountdown > 0 ? (
              <>
                <div className="flex items-center gap-2 text-blue-400 mb-1">
                  <Coffee className="w-5 h-5" />
                  <span className="text-sm font-medium">休息中 · 正在记录静息心率</span>
                </div>
                <div className="relative w-28 h-28">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
                    <circle cx="50" cy="50" r="44" fill="none" stroke="#3b82f6" strokeWidth="8" strokeLinecap="round"
                      strokeDasharray={2*Math.PI*44}
                      strokeDashoffset={2*Math.PI*44*(1-restProgress/100)}
                      className="transition-all duration-1000 ease-linear"
                      style={{ filter: "drop-shadow(0 0 8px rgba(59,130,246,0.5))" }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-bold tabular-nums text-foreground">{restCountdown}</span>
                    <span className="text-xs text-muted-foreground">秒</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-secondary/50 rounded-xl border border-border/30">
                  <Heart className="w-4 h-4 text-blue-400" />
                  <span className="text-sm text-foreground tabular-nums">{avgRestHrDisplay} <span className="text-xs text-muted-foreground">BPM</span></span>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2 text-emerald-400">
                <Heart className="w-5 h-5" />
                <span className="text-sm font-medium">休息完成 · 静息 {avgRestHrRef.current} BPM</span>
              </div>
            )}
          </div>

          {/* Input card */}
          <div className="w-full max-w-sm bg-card rounded-3xl border border-border/50 p-6 space-y-4 mx-auto">
            <div className="text-center">
              <div className="w-10 h-10 rounded-2xl bg-primary/20 flex items-center justify-center mx-auto mb-2">
                <Dumbbell className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-base font-bold text-foreground">记录本组数据</h3>
              <p className="text-xs text-muted-foreground">{currentExercise?.name}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="reps" className="text-sm text-muted-foreground">完成次数</Label>
                <Input id="reps" type="number" placeholder="12" value={setReps} onChange={(e) => setSetReps(e.target.value)}
                  className="h-12 bg-input border-border/50 rounded-xl text-center text-lg font-bold" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="weight" className="text-sm text-muted-foreground">重量 (kg)</Label>
                <Input id="weight" type="number" placeholder="80" value={setWeight} onChange={(e) => setSetWeight(e.target.value)}
                  className="h-12 bg-input border-border/50 rounded-xl text-center text-lg font-bold" />
              </div>
            </div>
            {setError && <p className="text-sm text-destructive text-center">{setError}</p>}
            {pendingSubmit.current && restCountdown > 0 && (
              <p className="text-xs text-blue-400 text-center">已记录，等待休息结束后自动提交...</p>
            )}
            <Button
              onClick={handleSaveSet}
              disabled={isSavingSet || (pendingSubmit.current && restCountdown > 0)}
              className="w-full h-12 text-base font-bold rounded-2xl bg-primary hover:bg-primary/90"
            >
              {isSavingSet
                ? <Loader2 className="w-5 h-5 animate-spin" />
                : restCountdown > 0
                  ? `等待休息结束 (${restCountdown}s)`
                  : "保存并分析"
              }
            </Button>
          </div>
        </div>
      )}

      {showSummary && summaryData && (
        <SummaryModal
          data={summaryData}
          exercises={exercises}
          currentExIdx={currentExIdx}
          onContinue={handleContinue}
          onAddExercise={onAddExercise}
        />
      )}
    </div>
  )
}

