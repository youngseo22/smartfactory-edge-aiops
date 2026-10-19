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
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => fire(0)}
        className={btn(normal, 'border-emerald-400 bg-emerald-500/20 text-emerald-300 shadow-emerald-500/20')}
        aria-label="정상화 (Normal)"
        title="모든 이상 상태를 해소하고 기본 정상 운영 모드로 복구합니다."
      >
        <span className="h-2 w-2 rounded-full bg-emerald-400" />
        <RotateCcw size={15} className={busy === 0 ? 'animate-spin' : ''} />
        <span className="text-xs">정상 운영</span>
      </button>
      <button
        onClick={() => fire(1)}
        className={btn(active.includes(1), 'border-orange-400 bg-orange-500/20 text-orange-300 shadow-orange-500/20')}
        aria-label="모터 이상 & 큐 적체"
        title="조립 모터 진동 급증 및 Pub/Sub 큐 병목 장애를 발생시킵니다."
      >
        <Flame size={15} className={busy === 1 ? 'animate-pulse text-orange-400' : ''} />
        <span className="text-xs font-medium">모터 이상·큐 적체</span>
      </button>
      <button
        onClick={() => fire(2)}
        className={btn(active.includes(2), 'border-sky-400 bg-sky-500/20 text-sky-300 shadow-sky-500/20')}
        aria-label="콜드체인 과온 & Failover"
        title="콜드체인 Zone A 온도 이상 및 Zone B 자동 절체(Failover)를 발생시킵니다."
      >
        <Snowflake size={15} className={busy === 2 ? 'animate-pulse text-sky-400' : ''} />
        <span className="text-xs font-medium">콜드체인 이상·Failover</span>
      </button>
    </div>
  )
}
