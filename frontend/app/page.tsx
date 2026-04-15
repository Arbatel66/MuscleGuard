"use client"

import { useState, useCallback } from "react"
import { LoginScreen } from "@/components/login-screen"
import { RegisterCard } from "@/components/register-card"
import { PlanSetupScreen } from "@/components/plan-setup-screen"
import { MuscleSelectScreen } from "@/components/muscle-select-screen"
import { ExerciseSelectScreen, type SelectedExercise } from "@/components/exercise-select-screen"
import { TrainingScreen } from "@/components/training-screen"
import { AiChatDrawer } from "@/components/ai-chat-drawer"
import { HistoryPlansScreen } from "@/components/history-plans-screen"

const API_BASE = "/api"
const HEADERS = { "ngrok-skip-browser-warning": "true" }
const JSON_HEADERS = { ...HEADERS, "Content-Type": "application/json" }

type AppState =
  | "login"
  | "register"
  | "plan-setup"
  | "history-plans"
  | "muscle-select"
  | "exercise-select"
  | "training"

interface UserData {
  name: string
  weight: number
  height: number
  age: number
  sessionId: string
}

interface PlanData {
  planId: number
  planName: string
}

interface HistorySetDetail {
  set_id: number
  weight: number
  reps: number
  peak_hr?: number | null
  rest_hr?: number | null
  score?: number | null
}

interface HistoryExerciseDetail {
  plan_id: number
  exercise_id: number
  exercise_base_id: string
  exercise_name: string
  sets: HistorySetDetail[]
}

interface HistoryPlanDetail {
  plan_name: string
  plan_id: number
  session_id: string
  start_time: string
  exercises: HistoryExerciseDetail[]
}

// ─── API layer ────────────────────────────────────────────────────────────────
const api = {
  checkSession: async (sessionId: string): Promise<UserData | null> => {
    try {
      const res = await fetch(`${API_BASE}/user/${sessionId}`, { headers: HEADERS })
      const data = await res.json()
      if (!data || data === "用户不存在" || !data.name) return null
      return {
        name: data.name,
        weight: data.weight,
        height: data.height,
        age: data.age,
        sessionId: data.session_id,
      }
    } catch {
      return null
    }
  },

  register: async (data: {
    sessionId: string; name: string
    height: number; weight: number; age: number
  }): Promise<UserData> => {
    const res = await fetch(`${API_BASE}/user/create`, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({
        session_id: data.sessionId,
        name: data.name,
        height: data.height,
        weight: data.weight,
        age: data.age,
      }),
    })
    if (!res.ok) throw new Error("Registration failed")
    return { ...data }
  },

  createPolling: async (sessionId: string): Promise<void> => {
    await fetch(`${API_BASE}/sync/create_polling?session_id=${sessionId}`, {
      method: "POST",
      headers: HEADERS,
    })
  },

  resumePolling: async (sessionId: string): Promise<void> => {
    await fetch(`${API_BASE}/sync/resume_polling?session_id=${encodeURIComponent(sessionId)}`, { method: "POST", headers: HEADERS })
  },

  pausePolling: async (params: {
    sessionId: string
    exerciseId: number
    reps: number
    weight: number
  }): Promise<{ set_id: number; score: number; peakHr: number; restHr: number; analysis: string }> => {
    const url = new URL(`${API_BASE}/sync/pause_polling`, window.location.origin)
    url.searchParams.set("session_id", params.sessionId)
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify({
        exercise_id: params.exerciseId,
        reps: params.reps,
        weight: params.weight,
      }),
    })
    const data = await res.json()
    return {
      set_id: data.set_id ?? 0,
      score: data.score ?? 60,
      peakHr: data.peak_hr ?? 0,
      restHr: data.rest_hr ?? 0,
      analysis: data.analysis ?? "训练完成，请继续保持！",
    }
  },

  getHeartRate: async (sessionId: string): Promise<number> => {
    try {
      const res = await fetch(
        `${API_BASE}/sync/current_hr?session_id=${encodeURIComponent(sessionId)}`,
        { headers: HEADERS }
      )
      const data = await res.json()
      // current_hr returns a bare number from Hyperate
      if (typeof data === "number" && data > 0) return data
      // fallback: object shape { last_value, status }
      if (data && typeof data.last_value === "number" && data.last_value > 0) return data.last_value
      return 0
    } catch {
      return 0
    }
  },

  getHistoryPlans: async (sessionId: string): Promise<HistoryPlanDetail[]> => {
    const res = await fetch(
      `${API_BASE}/exercise/get_plans?session_id=${encodeURIComponent(sessionId)}`,
      { headers: HEADERS }
    )
    if (!res.ok) throw new Error("加载历史计划失败")
    const data = await res.json()
    return Array.isArray(data) ? data : []
  },

}
// ─────────────────────────────────────────────────────────────────────────────

export default function MuscleGuardApp() {
  const [appState, setAppState] = useState<AppState>("login")
  const [userData, setUserData] = useState<UserData | null>(null)
  const [pendingSessionId, setPendingSessionId] = useState("")
  const [planData, setPlanData] = useState<PlanData | null>(null)
  const [selectedMuscle, setSelectedMuscle] = useState("")
  const [exercises, setExercises] = useState<SelectedExercise[]>([])
  const [historyPlans, setHistoryPlans] = useState<HistoryPlanDetail[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState("")

  // ── Auth ──
  const handleLogin = useCallback(async (sessionId: string): Promise<boolean> => {
    const user = await api.checkSession(sessionId)
    if (user) {
      setUserData(user)
      await api.createPolling(sessionId)
      setAppState("plan-setup")
      return true
    }
    return false
  }, [])

  const handleNeedRegister = useCallback((sessionId: string) => {
    setPendingSessionId(sessionId)
    setAppState("register")
  }, [])

  const handleRegister = useCallback(async (data: {
    sessionId: string; name: string
    height: number; weight: number; age: number
  }) => {
    const user = await api.register(data)
    setUserData(user)
    await api.createPolling(data.sessionId)
    setAppState("plan-setup")
  }, [])

  const handleBackToLogin = useCallback(() => {
    setAppState("login")
    setPendingSessionId("")
  }, [])

  const loadHistoryPlans = useCallback(async () => {
    const sessionId = userData?.sessionId
    if (!sessionId) return
    setHistoryLoading(true)
    setHistoryError("")
    try {
      const plans = await api.getHistoryPlans(sessionId)
      setHistoryPlans(plans)
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "加载历史计划失败")
    } finally {
      setHistoryLoading(false)
    }
  }, [userData?.sessionId])

  const handleOpenHistory = useCallback(async () => {
    await loadHistoryPlans()
    setAppState("history-plans")
  }, [loadHistoryPlans])

  // ── Plan ──
  const handlePlanCreated = useCallback((planId: number, planName: string) => {
    setPlanData({ planId, planName })
    setAppState("muscle-select")
  }, [])

  // ── Muscle ──
  const handleMuscleSelected = useCallback((muscle: string) => {
    setSelectedMuscle(muscle)
    setAppState("exercise-select")
  }, [])

  // ── Exercises ──
  const handleExercisesReady = useCallback((exs: SelectedExercise[]) => {
    setExercises(exs)
    setAppState("training")
  }, [])

  // ── Training: add exercise (go back to exercise-select with same plan) ──
  const handleAddExercise = useCallback(() => {
    setAppState("exercise-select")
  }, [])

  // ── Training API callbacks ──
  const fetchHeartRate = useCallback(
    () => api.getHeartRate(userData?.sessionId ?? ""),
    [userData?.sessionId]
  )
  const resumePolling = useCallback(() => api.resumePolling(userData?.sessionId ?? ""), [userData?.sessionId])
  const pausePolling = useCallback(
    (params: Parameters<typeof api.pausePolling>[0]) => api.pausePolling(params),
    []
  )

  // ── Render ──
  if (appState === "login") {
    return (
      <LoginScreen
        onLogin={handleLogin}
        onNeedRegister={handleNeedRegister}
      />
    )
  }

  if (appState === "register") {
    return (
      <RegisterCard
        sessionId={pendingSessionId}
        onRegister={handleRegister}
        onBack={handleBackToLogin}
      />
    )
  }

  // 登录后的所有页面都挂载 AiChatDrawer
  const chatDrawer = userData ? <AiChatDrawer sessionId={userData.sessionId} /> : null

  if (appState === "plan-setup" && userData) {
    return (
      <>
        <PlanSetupScreen
          userName={userData.name}
          sessionId={userData.sessionId}
          onPlanCreated={handlePlanCreated}
          onOpenHistory={handleOpenHistory}
        />
        {chatDrawer}
      </>
    )
  }

  if (appState === "history-plans" && userData) {
    return (
      <>
        <HistoryPlansScreen
          userData={userData}
          plans={historyPlans}
          loading={historyLoading}
          error={historyError}
          onBack={() => setAppState("plan-setup")}
          onRefresh={loadHistoryPlans}
        />
        {chatDrawer}
      </>
    )
  }

  if (appState === "muscle-select" && planData) {
    return (
      <>
        <MuscleSelectScreen
          planName={planData.planName}
          onMuscleSelected={handleMuscleSelected}
          onBack={() => setAppState("plan-setup")}
        />
        {chatDrawer}
      </>
    )
  }

  if (appState === "exercise-select" && planData) {
    return (
      <>
        <ExerciseSelectScreen
          planId={planData.planId}
          muscle={selectedMuscle}
          planName={planData.planName}
          onExercisesReady={handleExercisesReady}
          onBack={() => setAppState("muscle-select")}
        />
        {chatDrawer}
      </>
    )
  }

  if (appState === "training" && userData && exercises.length > 0) {
    return (
      <>
        <TrainingScreen
          userData={userData}
          exercises={exercises}
          onFetchHeartRate={fetchHeartRate}
          onResumePolling={resumePolling}
          onPausePolling={pausePolling}
          onAddExercise={handleAddExercise}
        />
        {chatDrawer}
      </>
    )
  }

  return null
}
 