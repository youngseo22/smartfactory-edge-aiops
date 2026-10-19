import { useState } from 'react'
import { Flame, RotateCcw, Snowflake } from 'lucide-react'
import { triggerScenario } from '../hooks/useDashboard'

interface Props {
  active: number[]
}

/** 시연용 장애 시나리오 강제 트리거 버튼 바 */
export default function ScenarioController({ active }: Props) {
  const [busy, setBusy] = useState<number | null>(null)

  const fire = async (id: 0 | 1 | 2) => {
    setBusy(id)
    try {
      await triggerScenario(id)
    } finally {
      setTimeout(() => setBusy(null), 400)
    }
  }

  const normal = active.length === 0
  const btn = (on: boolean, color: string) =>
    `flex items-center gap-2 rounded-lg border-2 px-3 py-1.5 text-sm font-semibold transition-all active:scale-95 ${
      on ? `${color} shadow-lg` : 'border-slate-700 bg-slate-800/70 text-slate-300 hover:border-slate-500'
    }`

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => fire(0)}
        className={btn(normal, 'border-emerald-400 bg-emerald-500/20 text-emerald-300 shadow-emerald-500/20')}
        aria-label="Normal"
      >
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
        <RotateCcw size={16} className={busy === 0 ? 'animate-spin' : ''} />
      </button>
      <button
        onClick={() => fire(1)}
        className={btn(active.includes(1), 'border-orange-400 bg-orange-500/20 text-orange-300 shadow-orange-500/20')}
        aria-label="Scenario 1"
      >
        <Flame size={16} className={busy === 1 ? 'animate-pulse' : ''} />
        <span className="font-mono">1</span>
      </button>
      <button
        onClick={() => fire(2)}
        className={btn(active.includes(2), 'border-sky-400 bg-sky-500/20 text-sky-300 shadow-sky-500/20')}
        aria-label="Scenario 2"
      >
        <Snowflake size={16} className={busy === 2 ? 'animate-pulse' : ''} />
        <span className="font-mono">2</span>
      </button>
    </div>
  )
}
