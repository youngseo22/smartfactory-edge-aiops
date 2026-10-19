import { useState } from 'react'
import { Activity, RotateCcw, ShieldCheck, Snowflake, TrendingUp, Wrench, Zap } from 'lucide-react'
import { triggerScenario } from '../hooks/useDashboard'
import type { Snapshot } from '../types'

interface Props {
  active: number[]
  snap?: Snapshot | null
}

/** 시연용 장애 시나리오 제어 바 */
export default function ScenarioController({ active, snap }: Props) {
  const [busy, setBusy] = useState<number | null>(null)

  const fire = async (id: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7) => {
    setBusy(id)
    try {
      await triggerScenario(id)
    } finally {
      setTimeout(() => setBusy(null), 400)
    }
  }

  // 주문 폭증 상태: active_scenarios에 3이 있더라도 파드가 1개 이하로 안정화되었으면 활성 표시 해제
  const activePodsCount = snap?.worker_pods?.filter((p) => p.status === 'ACTIVE').length ?? 0
  const isOrderBurstActive = active.includes(3) && activePodsCount > 1

  const normal = active.length === 0
  const btn = (on: boolean, color: string) =>
    `flex items-center gap-1.5 rounded-lg border-2 px-2.5 py-1.5 text-xs font-semibold transition-all active:scale-95 ${
      on ? `${color} shadow-lg` : 'border-slate-700 bg-slate-800/70 text-slate-300 hover:border-slate-500'
    }`

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* 1. 정상 운영 (Reset) */}
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
        className={btn(isOrderBurstActive, 'border-sky-400 bg-sky-500/20 text-sky-300 shadow-sky-500/20')}
        aria-label="주문 폭증"
        title="주문 1,250건 폭증 주입 ➔ Pub/Sub 큐 적체 & GKE 파드 자동 확장(Scale-up)"
      >
        <TrendingUp size={14} className={busy === 3 || isOrderBurstActive ? 'animate-bounce text-sky-400' : ''} />
        <span>주문 폭증</span>
      </button>

      {/* 3. 모터 교체 (현장 정비 완료 ➔ SVM 2.8 복귀 & 인터록 해제) */}
      <button
        onClick={() => fire(4)}
        className={btn(busy === 4, 'border-emerald-400 bg-emerald-500/25 text-emerald-300 shadow-emerald-500/20')}
        aria-label="모터 교체"
        title="현장 엔지니어가 모터를 신품으로 교체/정비하여 진동치를 정상화(2.8 m/s²)하고 안전 인터록을 해제합니다."
      >
        <Wrench size={14} className={busy === 4 ? 'animate-spin text-emerald-400' : 'text-slate-400'} />
        <span>모터 교체</span>
      </button>

      {/* 4. 컨베이어 라인 진동 / 비정상 급가속 */}
      <button
        onClick={() => fire(6)}
        className={btn(active.includes(6), 'border-orange-400 bg-orange-500/20 text-orange-300 shadow-orange-500/20')}
        aria-label="컨베이어 진동"
        title="컨베이어 인버터 이상으로 인한 비정상 급가속(2.8 m/s) 및 라인 진동"
      >
        <Zap size={14} className={busy === 6 || active.includes(6) ? 'animate-pulse text-orange-400' : ''} />
        <span>컨베이어 이상</span>
      </button>

      {/* 5. 컨베이어 라인 안정화 */}
      <button
        onClick={() => fire(7)}
        className={btn(busy === 7, 'border-emerald-400 bg-emerald-500/25 text-emerald-300 shadow-emerald-500/20')}
        aria-label="컨베이어 안정화"
        title="컨베이어 인버터 PID 파라미터 보정 ➔ 정속 1.0 m/s 복구"
      >
        <Activity size={14} className={busy === 7 ? 'animate-spin text-emerald-400' : 'text-slate-400'} />
        <span>컨베이어 안정화</span>
      </button>

      {/* 6. 콜드체인 이상 (Failover) */}
      <button
        onClick={() => fire(2)}
        className={btn(active.includes(2), 'border-amber-400 bg-amber-500/20 text-amber-300 shadow-amber-500/20')}
        aria-label="콜드체인 이상"
        title="Zone A 창고 온도 이상(8°C 초과) ➔ Zone B 무중단 자동 절체(Failover)"
      >
        <Snowflake size={14} className={busy === 2 || active.includes(2) ? 'animate-pulse text-amber-400' : ''} />
        <span>콜드체인 이상</span>
      </button>

      {/* 7. Zone A 복구 (냉각기/센서 수리 완료 ➔ Failback 원복) */}
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
