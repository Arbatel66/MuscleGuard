"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Bot, X, Send, Loader2, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

const API_BASE = "/api"
const HEADERS = { "ngrok-skip-browser-warning": "true", "Content-Type": "application/json" }

interface Message {
  id: number
  role: "user" | "ai"
  content: string
  pending?: boolean
}

interface AiChatDrawerProps {
  sessionId: string
}

export function AiChatDrawer({ sessionId }: AiChatDrawerProps) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      role: "ai",
      content: "你好！我是你的 AI 健身教练。可以问我训练建议、动作做法、历史记录，或者任何健身相关的问题。",
    },
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const idRef = useRef(1)

  // 自动滚到底部
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, open])

  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = { id: idRef.current++, role: "user", content: text }
    const pendingMsg: Message = { id: idRef.current++, role: "ai", content: "", pending: true }

    setMessages((prev) => [...prev, userMsg, pendingMsg])
    setInput("")
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat/ai_chat`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      const data = await res.json()
      const reply: string = data.reply ?? "抱歉，我暂时无法回复，请稍后再试。"
      setMessages((prev) =>
        prev.map((m) => (m.pending ? { ...m, content: reply, pending: false } : m))
      )
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.pending ? { ...m, content: "网络异常，请稍后重试。", pending: false } : m
        )
      )
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }, [input, loading, sessionId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* ── 悬浮触发按钮 ── */}
      <button
        onClick={() => setOpen(true)}
        aria-label="打开 AI 教练"
        className="
          fixed bottom-6 right-5 z-40
          w-14 h-14 rounded-full
          bg-primary shadow-lg shadow-primary/40
          flex items-center justify-center
          transition-all duration-200
          hover:scale-110 active:scale-95
          border border-primary/30
        "
        style={{ display: open ? "none" : "flex" }}
      >
        <Bot className="w-6 h-6 text-primary-foreground" />
      </button>

      {/* ── 抽屉遮罩 ── */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex flex-col"
          style={{ background: "oklch(0.08 0 0)" }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 pt-12 pb-4 border-b border-border/40">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-foreground">AI 健身教练</p>
              <p className="text-xs text-muted-foreground truncate">可查询训练记录 · 动作指导 · 个性化建议</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-2 rounded-xl hover:bg-secondary/60 transition-colors"
            >
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2.5 ${
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                {/* Avatar */}
                {msg.role === "ai" && (
                  <div className="w-7 h-7 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 text-primary" />
                  </div>
                )}

                {/* Bubble */}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-sm"
                      : "bg-secondary/60 text-foreground border border-border/30 rounded-tl-sm"
                  }`}
                >
                  {msg.pending ? (
                    <span className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span className="text-xs">思考中...</span>
                    </span>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="px-4 pb-8 pt-3 border-t border-border/40">
            <div className="flex gap-2 items-end bg-secondary/40 rounded-2xl border border-border/40 p-2">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="问我任何健身问题...（Enter 发送）"
                rows={1}
                disabled={loading}
                className="
                  flex-1 resize-none border-0 bg-transparent shadow-none
                  text-sm text-foreground placeholder:text-muted-foreground
                  focus-visible:ring-0 min-h-[36px] max-h-[120px] py-2 px-2
                "
                style={{ fieldSizing: "content" } as React.CSSProperties}
              />
              <Button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                size="icon"
                className="
                  w-9 h-9 rounded-xl flex-shrink-0
                  bg-primary hover:bg-primary/90
                  disabled:opacity-30 transition-all
                "
              >
                {loading
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Send className="w-4 h-4" />}
              </Button>
            </div>
            <p className="text-center text-xs text-muted-foreground/50 mt-2">Shift+Enter 换行</p>
          </div>
        </div>
      )}
    </>
  )
}
