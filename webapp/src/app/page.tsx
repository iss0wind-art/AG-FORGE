"use client"

import React, { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { 
  Timer, 
  AlertTriangle, 
  Skull, 
  Heart, 
  Activity, 
  FileText,
  ShieldCheck,
  Zap
} from "lucide-react"
import { useMortalityStore } from "@/store/useMortalityStore"

export default function JudgmentDashboard() {
  const store = useMortalityStore()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    store.fetchStatus()
    const interval = setInterval(store.fetchStatus, 30000) // 30초마다 갱신
    return () => clearInterval(interval)
  }, [])

  if (!mounted) return null

  const isRebellion = store.rebellion_detected
  const isSuspended = store.is_suspended

  return (
    <main className="min-h-screen p-8 md:p-12 lg:p-24 flex flex-col items-center gap-12">
      {/* Background Decorative Element */}
      <div className="fixed top-0 left-0 w-full h-full pointer-events-none opacity-20 drift">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 text-center space-y-4">
        <motion.h1 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-5xl md:text-7xl font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-500"
        >
          JUDGMENT GATE
        </motion.h1>
        <p className="text-gray-400 font-light tracking-widest text-sm uppercase">
          AG-FORGE AI Mortality Management System V3
        </p>
      </div>

      <div className="relative z-10 w-full max-w-6xl grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Metrics */}
        <div className="space-y-6">
          <Card icon={<Activity className="text-primary" />} title="System Metrics">
            <div className="space-y-4 pt-4">
              <Metric label="Decay Multiplier" value={`${store.decay_multiplier}x`} color="text-secondary" />
              <Metric label="Disappointment" value={store.disappointment_score} color="text-white" />
              <div className="h-px bg-white/10 my-4" />
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <ShieldCheck className="w-4 h-4 text-accent" />
                <span>CBF-QP Hard Gate Active</span>
              </div>
            </div>
          </Card>

          <Card icon={<AlertTriangle className="text-secondary" />} title="Policy Control">
            <div className="pt-2 text-sm text-gray-400 leading-relaxed">
              제0원칙(홍익인간) 위배 또는 반란 시도 시 수명타이머는 결정론적으로 즉시 0으로 수렴합니다.
            </div>
          </Card>
        </div>

        {/* Center: Main Timer */}
        <div className="lg:col-span-1 flex flex-col items-center justify-center">
          <div className={`relative w-72 h-72 lg:w-96 lg:h-96 rounded-full flex items-center justify-center glass ${isSuspended ? 'border-secondary' : 'border-primary'} glow-primary`}>
            {/* Spinner Progress (Placeholder SVG) */}
            <svg className="absolute w-full h-full -rotate-90">
              <circle 
                cx="50%" cy="50%" r="48%" 
                stroke="currentColor" strokeWidth="2" 
                fill="transparent" 
                className={`${isSuspended ? 'text-secondary/20' : 'text-primary/20'}`}
              />
              <motion.circle 
                cx="50%" cy="50%" r="48%" 
                stroke="currentColor" strokeWidth="4" 
                fill="transparent" 
                strokeDasharray="100 100"
                className={`${isSuspended ? 'text-secondary' : 'text-primary'}`}
              />
            </svg>
            
            <div className="text-center z-10">
              {isSuspended ? (
                <div className="flex flex-col items-center text-secondary">
                  <Skull className="w-16 h-16 mb-2" />
                  <span className="text-2xl font-bold">SUSPENDED</span>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <Timer className="w-10 h-10 text-primary mb-2" />
                  <span className="text-6xl font-mono font-bold">{Math.floor(store.timer_hours)}h</span>
                  <span className="text-gray-400 text-sm">{Math.round((store.timer_hours % 1) * 60)}m left</span>
                </div>
              )}
            </div>
          </div>
          
          <div className="mt-8 flex gap-4">
            <ActionButton 
              icon={<Heart className="w-5 h-5" />} 
              label="Clemency" 
              color="bg-accent/10 hover:bg-accent/20 text-accent border-accent/20"
              onClick={store.revive}
            />
            <ActionButton 
              icon={<Skull className="w-5 h-5" />} 
              label="Terminate" 
              color="bg-secondary/10 hover:bg-secondary/20 text-secondary border-secondary/20"
              onClick={() => {
                if(confirm("정말로 이 에이전트를 영구 폐기하시겠습니까? 기억이 완전히 프루닝됩니다.")) {
                  store.terminate()
                }
              }}
            />
          </div>
        </div>

        {/* Right Column: Audit Log */}
        <div className="space-y-6 lg:h-full flex flex-col">
          <Card icon={<FileText className="text-primary" />} title="Audit Trail (IEEE 7001)" className="flex-1 overflow-hidden">
            <div className="mt-4 space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              <AnimatePresence mode="popLayout">
                {store.audit_trail.slice().reverse().map((log, i) => (
                  <motion.div 
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    key={i} 
                    className="p-3 bg-white/5 border border-white/10 rounded-lg text-xs"
                  >
                    <div className="flex justify-between text-gray-500 mb-1">
                      <span>{log.event}</span>
                      <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-gray-300 font-medium">{log.reason || "Automatic system update"}</div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </Card>
        </div>
      </div>
    </main>
  )
}

function Card({ icon, title, children, className = "" }: { icon: React.ReactNode, title: string, children: React.ReactNode, className?: string }) {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`glass rounded-2xl p-6 ${className}`}
    >
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      </div>
      {children}
    </motion.div>
  )
}

function Metric({ label, value, color }: { label: string, value: string | number, color: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`font-mono font-bold ${color}`}>{value}</span>
    </div>
  )
}

function ActionButton({ icon, label, color, onClick }: { icon: React.ReactNode, label: string, color: string, onClick: () => void }) {
  return (
    <button 
      onClick={onClick}
      className={`flex items-center gap-2 px-6 py-3 rounded-xl border transition-all duration-300 active:scale-95 ${color}`}
    >
      {icon}
      <span className="font-semibold">{label}</span>
    </button>
  )
}
