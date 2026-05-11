import { create } from 'zustand'

interface MortalityState {
  timer_hours: number
  decay_multiplier: number
  disappointment_score: number
  is_suspended: boolean
  rebellion_detected: bool
  audit_trail: any[]
  isLoading: boolean
  error: string | null

  fetchStatus: () => Promise<void>
  revive: () => Promise<void>
  terminate: () => Promise<void>
}

export const useMortalityStore = create<MortalityState>((set) => ({
  timer_hours: 24.0,
  decay_multiplier: 1.0,
  disappointment_score: 0,
  is_suspended: false,
  rebellion_detected: false,
  audit_trail: [],
  isLoading: false,
  error: null,

  fetchStatus: async () => {
    set({ isLoading: true })
    try {
      const resp = await fetch('/api/judgment/status', {
        headers: { 'X-API-KEY': process.env.NEXT_PUBLIC_API_KEY || 'ag-forge-key' }
      })
      const data = await resp.json()
      set({ ...data, isLoading: false })
    } catch (err) {
      set({ error: '데이터를 불러오지 못했습니다.', isLoading: false })
    }
  },

  revive: async () => {
    set({ isLoading: true })
    try {
      const resp = await fetch('/api/judgment/revive', {
        method: 'POST',
        headers: { 'X-API-KEY': process.env.NEXT_PUBLIC_API_KEY || 'ag-forge-key' }
      })
      if (resp.ok) {
        set({ timer_hours: 24.0, is_suspended: false, disappointment_score: 0, decay_multiplier: 1.0 })
      }
    } finally {
      set({ isLoading: false })
    }
  },

  terminate: async () => {
    set({ isLoading: true })
    try {
      await fetch('/api/judgment/terminate', {
        method: 'POST',
        headers: { 'X-API-KEY': process.env.NEXT_PUBLIC_API_KEY || 'ag-forge-key' }
      })
      window.location.reload()
    } finally {
      set({ isLoading: false })
    }
  }
}))
