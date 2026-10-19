import { useState } from 'react'
import { Flame, RotateCcw, ShieldCheck, Snowflake, TrendingUp, Wrench } from 'lucide-react'
import { triggerScenario } from '../hooks/useDashboard'

interface Props {
  active: number[]
}

/** 시연용 장애 시나리오 강제 트리거 버튼 바 */
export default function ScenarioController({ active }: Props) {
  const [busy, setBusy] = useState<number | null>(null)

  const fire = async (id: 0 | 1 | 2 | 3 | 4 | 5) => {
    setBusy(id)
    try {
      await triggerScenario(id)
    } finally {
      setTimeout(() => setBusy(null), 400)
    }
  }

  const normal = active.length === 0
  const btn = (on: boolean, color: string) =>
    `flex items-center gap-1.5 rounded-lg border-2 px-2.5 py-1.5 text-xs font-semibold transition-all active:scale-95 ${
      on ? `${color} shadow-lg` : 'border-slate-700 bg-slate-800/70 text-slate-300 hover:border-slate-500'
    }`

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* 1. 정상 운영 */}
      <button
        onClick={() => fire(0)}
        className={btn(normal, 'border-emerald-400 bg-emerald-500/20 text-emerald-300 shadow-emerald-500/20')}
        aria-label="정상 운영"
        title="모든 시스템을 초기 정상 상태로 복구합니다."
      >
        <RotateCcw size={14} className={busy === 0 ? 'animate-spin text-emerald-400' : ''} />
        <span>정상 운영</span>
      </button>

      {/* 2. 주문 폭증 (HPA 스케일아웃) */}
      <button
        onClick={() => fire(3)}
        className={btn(active.includes(3), 'border-sky-400 bg-sky-500/20 text-sky-300 shadow-sky-500/20')}
        aria-label="주문 폭증"
        title="주문 1,250건 폭증 주입 ➔ Pub/Sub 큐 적체 & GKE 파드 자동 확장(Scale-up)"
      >
        <TrendingUp size={14} className={busy === 3 || active.includes(3) ? 'animate-bounce text-sky-400' : ''} />
        <span>주문 폭증</span>
      </button>

      {/* 3. 모터 불량 (진동 이상 & Slack RAG) */}
      <button
        onClick={() => fire(1)}
        className={btn(active.includes(1), 'border-red-400 bg-red-500/20 text-red-300 shadow-red-500/20')}
        aria-label="모터 불량"
        title="조립 모터 진동 결함(SVM 8.5) ➔ 컨베이어 흔들림 & Slack RAG 정비 매뉴얼 알림 발송"
      >
        <Flame size={14} className={busy === 1 || active.includes(1) ? 'animate-pulse text-red-400' : ''} />
        <span>모터 불량</span>
      </button>

      {/* 4. 모터 교체 (현장 정비 완료 ➔ 진동 해제) */}
      <button
        onClick={() => fire(4)}
        className={btn(busy === 4, 'border-emerald-400 bg-emerald-500/25 text-emerald-300 shadow-emerald-500/20')}
        aria-label="모터 교체"
        title="현장 엔지니어가 모터를 교체/정비하여 진동 경보를 즉시 해제합니다."
      >
        <Wrench size={14} className={busy === 4 ? 'animate-spin text-emerald-400' : 'text-slate-400'} />
        <span>모터 교체</span>
      </button>

      {/* 5. 콜드체인 이상 (Failover) */}
      <button
        onClick={() => fire(2)}
        className={btn(active.includes(2), 'border-amber-400 bg-amber-500/20 text-amber-300 shadow-amber-500/20')}
        aria-label="콜드체인 이상"
        title="Zone A 창고 온도 이상(8°C 초과) ➔ Zone B 무중단 자동 절체(Failover)"
      >
        <Snowflake size={14} className={busy === 2 || active.includes(2) ? 'animate-pulse text-amber-400' : ''} />
        <span>콜드체인 이상</span>
      </button>

      {/* 6. Zone A 복구 (냉각기/센서 수리 완료 ➔ Failback 원복) */}
      <button
        onClick={() => fire(5)}
        className={btn(busy === 5, 'border-teal-400 bg-teal-500/25 text-teal-300 shadow-teal-500/20')}
        aria-label="Zone A 복구"
        title="Zone A 냉각기 수리 및 센서 통신 복구 ➔ 주 보관소(Zone A)로 Failback 원복"
      >
        <ShieldCheck size={14} className={busy === 5 ? 'animate-spin text-teal-400' : 'text-slate-400'} />
        <span>Zone A 복구</span>
      </button>
    </div>
  )
}
