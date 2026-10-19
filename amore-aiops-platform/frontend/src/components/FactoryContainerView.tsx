import { motion } from 'framer-motion'
import { AlertTriangle, Container, Cog, Zap } from 'lucide-react'
import type { PodState, Snapshot } from '../types'

const SVM_MAX = 10
const SVM_WARN = 7

/** 반원형 SVM 계기판 (0–4 정상 / 4–7 주의 / 7–10 위험) */
function SvmGauge({ value }: { value: number }) {
  const cx = 70
  const cy = 70
  const r = 52
  const pt = (v: number) => {
    const a = Math.PI * (1 - v / SVM_MAX)
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)] as const
  }
  const arc = (v0: number, v1: number) => {
    const [x0, y0] = pt(v0)
    const [x1, y1] = pt(v1)
    return `M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`
  }
  const deg = -90 + Math.min(1, Math.max(0, value / SVM_MAX)) * 180
  const danger = value >= SVM_WARN
  return (
    <svg viewBox="0 0 140 84" className="w-40">
      <path d={arc(0, 4)} stroke="#10b981" strokeWidth="9" fill="none" strokeLinecap="round" />
      <path d={arc(4, SVM_WARN)} stroke="#f59e0b" strokeWidth="9" fill="none" />
      <path d={arc(SVM_WARN, SVM_MAX)} stroke="#ef4444" strokeWidth="9" fill="none" strokeLinecap="round" />
      <g style={{ transformOrigin: `${cx}px ${cy}px`, transform: `rotate(${deg}deg)`, transition: 'transform .45s cubic-bezier(.3,1.4,.5,1)' }}>
        <line x1={cx} y1={cy} x2={cx} y2={cy - r + 6} stroke={danger ? '#fca5a5' : '#e2e8f0'} strokeWidth="3" strokeLinecap="round" />
      </g>
      <circle cx={cx} cy={cy} r="5" fill="#0f172a" stroke="#94a3b8" strokeWidth="2" />
      <text x={cx} y={cy + 13} textAnchor="middle" fontSize="13" fontWeight="700" fontFamily="monospace" fill={danger ? '#f87171' : '#e2e8f0'}>
        {value.toFixed(1)}
      </text>
    </svg>
  )
}

function Pod({ pod }: { pod: PodState }) {
  const style =
    pod.status === 'ACTIVE'
      ? 'border-emerald-500 bg-emerald-500/15 text-emerald-300'
      : pod.status === 'STARTING'
        ? 'border-sky-400 bg-sky-500/20 text-sky-300'
        : 'border-slate-700 bg-slate-800/60 text-slate-500'
  const led = pod.status === 'ACTIVE' ? 'bg-emerald-400' : pod.status === 'STARTING' ? 'bg-sky-400' : 'bg-slate-600'
  return (
    // key 에 status 를 포함 → 상태가 바뀔 때마다 점등 애니메이션 재생
    <motion.div
      key={`${pod.id}-${pod.status}`}
      initial={pod.status === 'STANDBY' ? false : { scale: 0.7, opacity: 0.4 }}
      animate={{
        scale: 1,
        opacity: 1,
        boxShadow:
          pod.status === 'STANDBY'
            ? '0 0 0 0 rgba(0,0,0,0)'
            : ['0 0 0 0 rgba(56,189,248,0.8)', '0 0 18px 4px rgba(56,189,248,0.0)'],
      }}
      transition={{ duration: 0.6 }}
      className={`relative flex flex-col items-center gap-1 rounded-lg border-2 px-2 pb-2 pt-1.5 ${style}`}
    >
      <div className="flex w-full items-center justify-between">
        <span className="font-mono text-[10px]">#{pod.id}</span>
        <span className={`h-2 w-2 rounded-full ${led} ${pod.status === 'STARTING' ? 'animate-blink' : ''}`} />
      </div>
      {pod.status === 'STARTING' ? (
        <motion.div animate={{ scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] }} transition={{ duration: 0.5, repeat: Infinity }}>
          <Zap size={22} className="fill-sky-300" />
        </motion.div>
      ) : (
        <Container size={22} />
      )}
      <div className="h-1 w-full overflow-hidden rounded-full bg-slate-900">
        <motion.div className="h-full bg-emerald-400" animate={{ width: `${pod.status === 'ACTIVE' ? Math.max(6, pod.load_pct) : 0}%` }} />
      </div>
    </motion.div>
  )
}

export default function FactoryContainerView({ snap }: { snap: Snapshot }) {
  const { motor, worker_pods: pods } = snap
  const fault = motor.svm >= SVM_WARN
  const spinDur = fault ? 0.9 : 3.2
  const beltCls = fault ? 'animate-belt-fast' : 'animate-belt'
  const bottleDur = fault ? 3 : 6

  return (
    <section className="panel panel-rivets relative flex flex-col gap-3 p-4">
      {/* ── 모터 + 계기판 ── */}
      <div className={`relative flex items-center justify-around rounded-lg border-2 p-3 transition-colors ${fault ? 'border-red-500 bg-red-950/30' : 'border-slate-700 bg-slate-950/60'}`}>
        {fault && (
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-lg"
            animate={{ boxShadow: ['inset 0 0 0 0 rgba(239,68,68,0)', 'inset 0 0 36px 6px rgba(239,68,68,0.55)', 'inset 0 0 0 0 rgba(239,68,68,0)'] }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        )}
        {/* 캡 조립 모터 #1 — 평상시 Spin, 과부하 시 Shake */}
        <motion.div
          className="relative"
          animate={fault ? { x: [0, -4, 4, -3, 3, 0], y: [0, 2, -2, 1, -1, 0] } : { x: 0, y: 0 }}
          transition={fault ? { duration: 0.28, repeat: Infinity } : { duration: 0.2 }}
        >
          <motion.div
            className={`flex h-24 w-24 items-center justify-center rounded-full border-4 ${fault ? 'border-red-500 text-red-400' : 'border-slate-600 text-sky-300'} bg-slate-900`}
            animate={{ rotate: 360 }}
            transition={{ duration: spinDur, repeat: Infinity, ease: 'linear' }}
          >
            <Cog size={58} strokeWidth={1.6} />
          </motion.div>
          <span className="absolute -left-2 -top-2 flex h-7 w-7 items-center justify-center rounded-md bg-slate-800 font-mono text-xs text-slate-300">#1</span>
          {fault && (
            <motion.div className="absolute -right-3 -top-3 text-red-400" animate={{ opacity: [1, 0.1, 1], scale: [1, 1.2, 1] }} transition={{ duration: 0.5, repeat: Infinity }}>
              <AlertTriangle size={28} className="fill-red-500/30" />
            </motion.div>
          )}
        </motion.div>

        <div className="flex flex-col items-center">
          <SvmGauge value={motor.svm} />
          <div className="mt-1 flex gap-3 font-mono text-[11px] text-slate-400">
            <span>{motor.torque_nm.toFixed(1)} N·m</span>
            <span>{Math.round(motor.rpm)} rpm</span>
          </div>
        </div>
      </div>

      {/* ── 컨베이어 벨트 ── */}
      <div className="relative h-14 overflow-hidden rounded-lg border-2 border-slate-700 bg-slate-950">
        <div
          className={`absolute inset-x-0 bottom-0 h-4 ${beltCls}`}
          style={{ background: 'repeating-linear-gradient(90deg,#334155 0 12px,#1e293b 12px 24px)' }}
        />
        {[0, 1, 2, 3, 4].map((i) => (
          <motion.span
            key={`${i}-${bottleDur}`}
            className="absolute bottom-3 text-2xl"
            initial={{ left: '-8%' }}
            animate={{ left: '104%' }}
            transition={{ duration: bottleDur, repeat: Infinity, ease: 'linear', delay: (i * bottleDur) / 5 }}
          >
            🧴
          </motion.span>
        ))}
      </div>

      {/* ── GKE Worker Container Rack ── */}
      <div className="rounded-lg border-2 border-slate-700 bg-slate-950/60 p-2">
        <div className="mb-2 flex items-center justify-between px-1 text-slate-400">
          <Container size={16} />
          <span className="font-mono text-xs">
            {pods.filter((p) => p.status === 'ACTIVE').length}/{pods.length}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {pods.map((p) => (
            <Pod key={p.id} pod={p} />
          ))}
        </div>
      </div>
    </section>
  )
}
