import { motion } from 'framer-motion'
import { Container, Cpu, Zap } from 'lucide-react'
import type { PodState, Snapshot } from '../types'

function Pod({ pod }: { pod: PodState }) {
  const style =
    pod.status === 'ACTIVE'
      ? 'border-emerald-500 bg-emerald-500/15 text-emerald-300'
      : pod.status === 'STARTING'
        ? 'border-sky-400 bg-sky-500/20 text-sky-300'
        : pod.status === 'TERMINATING'
          ? 'border-amber-400/80 bg-amber-500/15 text-amber-300'
          : 'border-slate-700 bg-slate-800/60 text-slate-500'
  const led =
    pod.status === 'ACTIVE'
      ? 'bg-emerald-400'
      : pod.status === 'STARTING'
        ? 'bg-sky-400'
        : pod.status === 'TERMINATING'
          ? 'bg-amber-400'
          : 'bg-slate-600'
  const statusLabel =
    pod.status === 'ACTIVE'
      ? '활성'
      : pod.status === 'STARTING'
        ? '기동 중'
        : pod.status === 'TERMINATING'
          ? '종료 중'
          : '대기'

  return (
    <motion.div
      key={`${pod.id}-${pod.status}`}
      initial={{ scale: 0.95 }}
      animate={{
        scale: 1,
        boxShadow:
          pod.status === 'ACTIVE'
            ? ['0 0 0 0 rgba(16,185,129,0.7)', '0 0 12px 2px rgba(16,185,129,0.0)']
            : pod.status === 'TERMINATING'
              ? ['0 0 0 0 rgba(245,158,11,0.8)', '0 0 16px 3px rgba(245,158,11,0.0)']
              : ['0 0 0 0 rgba(56,189,248,0.8)', '0 0 18px 4px rgba(56,189,248,0.0)'],
      }}
      transition={{ duration: 0.6 }}
      className={`relative flex flex-col items-center gap-1 rounded-lg border-2 px-2 pb-2 pt-1.5 ${style}`}
    >
      <div className="flex w-full items-center justify-between">
        <span className="font-mono text-[11px] font-bold">Pod #{pod.id}</span>
        <div className="flex items-center gap-1">
          <span className="text-[9px] font-medium opacity-80">{statusLabel}</span>
          <span
            className={`h-2 w-2 rounded-full ${led} ${
              pod.status === 'STARTING' ? 'animate-blink' : pod.status === 'TERMINATING' ? 'animate-pulse' : ''
            }`}
          />
        </div>
      </div>
      {pod.status === 'STARTING' ? (
        <motion.div animate={{ scale: [1, 1.25, 1], rotate: [0, 10, -10, 0] }} transition={{ duration: 0.5, repeat: Infinity }}>
          <Zap size={22} className="fill-sky-300" />
        </motion.div>
      ) : pod.status === 'TERMINATING' ? (
        <motion.div animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 0.5, repeat: Infinity }}>
          <Container size={22} className="text-amber-400" />
        </motion.div>
      ) : (
        <Container size={22} />
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-900 mt-0.5">
        <motion.div
          className={`h-full ${pod.status === 'TERMINATING' ? 'bg-amber-400' : 'bg-emerald-400'}`}
          animate={{ width: `${pod.status === 'ACTIVE' || pod.status === 'TERMINATING' ? Math.max(6, pod.load_pct) : 0}%` }}
        />
      </div>
      <span className="font-mono text-[10px] text-slate-300 font-medium">
        {pod.status === 'ACTIVE'
          ? `부하 ${Math.round(pod.load_pct)}%`
          : pod.status === 'STARTING'
            ? '프로비저닝'
            : pod.status === 'TERMINATING'
              ? '종료 드레인'
              : '대기 (Idle)'}
      </span>
    </motion.div>
  )
}

export default function ProcessingContainerView({ snap }: { snap: Snapshot }) {
  const pods = snap.worker_pods
  const activeCount = pods.filter((p) => p.status === 'ACTIVE').length
  const startingCount = pods.filter((p) => p.status === 'STARTING').length
  const terminatingCount = pods.filter((p) => p.status === 'TERMINATING').length

  return (
    <section className="panel panel-rivets relative flex flex-col justify-between gap-3 p-4">
      {/* ── 섹션 헤더 ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500/20 text-sky-400">
            <Cpu size={18} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>SECTION 4 : 처리 컨테이너</span>
              <span className="rounded bg-sky-950 px-2 py-0.5 text-[10px] font-normal text-sky-300 border border-sky-800">
                GKE Pod Rack
              </span>
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="rounded bg-sky-500/15 px-2 py-0.5 font-bold text-sky-300 border border-sky-500/30">
            가동 {activeCount}대 {startingCount > 0 && `(+${startingCount})`} {terminatingCount > 0 && `(-${terminatingCount})`} / 총 {pods.length}
          </span>
        </div>
      </div>

      {/* ── 컨테이너 파드 랙 그리드 (6 Pods) ── */}
      <div className="rounded-lg border-2 border-slate-700 bg-slate-950/60 p-3">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-1.5 text-xs text-slate-300">
          <div className="flex items-center gap-1.5">
            <Container size={15} className="text-sky-400 shrink-0" />
            <span className="font-bold text-slate-200 text-xs">스트림 처리 컨테이너 풀 (KEDA HPA)</span>
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            소비 속도: <b className="text-sky-300 font-semibold">{snap.pipeline.drain_rate} msg/s</b>
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {pods.map((p) => (
            <Pod key={p.id} pod={p} />
          ))}
        </div>

        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-1.5 border-t border-slate-800/80 pt-2 text-[10px] text-slate-400">
          <span className="text-slate-400 whitespace-nowrap">※ 큐 적체 시 6대로 자동 스케일아웃</span>
          <div className="flex items-center gap-2 font-mono">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-400" />활성</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-400" />기동</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />종료</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-slate-600" />대기</span>
          </div>
        </div>
      </div>

      {/* ── 하단 파드 상태 요약 바 ── */}
      <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2 text-xs">
        <span className="text-[11px] text-slate-400">오토스케일링 정책:</span>
        <span className="font-mono text-[11px] font-semibold text-emerald-300">
          {activeCount > 2 ? '⚡ HPA 스케일업 운용 중 (부하 분산)' : '🌱 기본 2파드 최적화 (절전 대기)'}
        </span>
      </div>
    </section>
  )
}
