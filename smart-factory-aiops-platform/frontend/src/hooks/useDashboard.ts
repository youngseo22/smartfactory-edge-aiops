import { useEffect, useRef, useState } from 'react'
import type { Snapshot } from '../types'

const WS_URL =
  import.meta.env.VITE_WS_URL ??
  `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/dashboard`

/** /ws/dashboard 구독 — 0.5초마다 도착하는 스냅샷을 상태로 보관, 끊기면 자동 재연결 */
export function useDashboard() {
  const [snap, setSnap] = useState<Snapshot | null>(null)
  const [connected, setConnected] = useState(false)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    let ws: WebSocket | null = null
    let timer: number | undefined

    const connect = () => {
      ws = new WebSocket(WS_URL)
      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => {
        try {
          setSnap(JSON.parse(e.data) as Snapshot)
        } catch {
          /* 잘못된 프레임 무시 */
        }
      }
      ws.onclose = () => {
        setConnected(false)
        if (alive.current) timer = window.setTimeout(connect, 1000)
      }
      ws.onerror = () => ws?.close()
    }
    connect()

    return () => {
      alive.current = false
      window.clearTimeout(timer)
      ws?.close()
    }
  }, [])

  return { snap, connected }
}

export async function triggerScenario(id: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7): Promise<void> {
  await fetch(`/api/scenario/${id}`, { method: 'POST' })
}

export async function stepMotorSvm(delta: number = 1.5): Promise<void> {
  await fetch(`/api/motor/svm/step?delta=${delta}`, { method: 'POST' })
}
