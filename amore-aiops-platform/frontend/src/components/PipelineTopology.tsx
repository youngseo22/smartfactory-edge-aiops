import { motion } from 'framer-motion'
import { AlertTriangle, Bot, Cloud, Cpu, Database, Network } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Snapshot } from '../types'

const TANK_MAX = 1500 // 탱크 눈금 최대(건)
const THRESHOLD = 1000

/** 파이프 위를 흐르는 데이터 패킷 — 유입 속도(msg/s)에 비례해 개수·속도 증가 (로그 스케일) */
function Pipe({ rate, color, label, className = '' }: { rate: number; color: string; label?: string; className?: string }) {
  const n = rate <= 0.1 ? 0 : Math.min(8, Math.max(1, Math.round(Math.log2(rate + 1))))
  const dur = Math.min(2.4, Math.max(0.5, 2.4 - Math.log10(rate + 1) * 0.7))
  return (
    <div className={`relative flex flex-col items-center justify-center shrink-0 w-28 sm:w-32 md:w-36 ${className}`}>
      {label && <span className="mb-1 font-mono text-[10px] text-slate-400 whitespace-nowrap">{label}</span>}
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div className="absolute inset-0 rounded-full opacity-30" style={{ background: color }} />
        {Array.from({ length: n }).map((_, i) => (
          <motion.span
            key={`${n}-${i}`}
            className="absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full"
            style={{ background: color, boxShadow: `0 0 8px 2px ${color}` }}
            initial={{ left: '-5%' }}
            animate={{ left: '105%' }}
            transition={{ duration: dur, repeat: Infinity, ease: 'linear', delay: (i * dur) / n }}
          />
        ))}
      </div>
    </div>
  )
}

function Node({
  icon,
  name,
  subtext,
  tone = 'slate',
  pulse = false,
  badge,
  badgePrefix = '',
}: {
  icon: ReactNode
  name: string
  subtext: string
  tone?: 'slate' | 'sky' | 'amber' | 'red' | 'emerald' | 'violet'
  pulse?: boolean
  badge?: string
  badgePrefix?: string
}) {
  const tones: Record<string, string> = {
    slate: 'border-slate-600 text-slate-300',
    sky: 'border-sky-500 text-sky-300',
    amber: 'border-amber-500 text-amber-300',
    red: 'border-red-500 text-red-300',
    emerald: 'border-emerald-500 text-emerald-300',
    violet: 'border-violet-500 text-violet-300',
  }
  return (
    <div className="relative flex flex-col items-center gap-1.5 w-28 shrink-0 text-center">
      <motion.div
        className={`flex h-13 w-13 items-center justify-center rounded-2xl border-2 bg-slate-900 ${tones[tone]} shadow-md`}
        animate={pulse ? { boxShadow: ['0 0 0 0 rgba(239,68,68,0.6)', '0 0 0 12px rgba(239,68,68,0)'] } : {}}
        transition={{ duration: 1, repeat: Infinity }}
      >
        {icon}
      </motion.div>
      <div className="flex flex-col items-center">
        <span className="text-xs font-bold text-slate-200">{name}</span>
        <span className="text-[10px] text-slate-400">{subtext}</span>
      </div>
      {badge !== undefined && (
        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] text-sky-300 border border-slate-700">
          {badgePrefix}{badge}
        </span>
      )}
    </div>
  )
}

/** Pub/Sub 실린더 탱크: 적체량을 액체 높이로 표현. 1,000건 초과 시 주황→빨강 + 경고등 점멸 */
function QueueTank({ backlog, severity }: { backlog: number; severity: 'OK' | 'WARN' | 'CRIT' }) {
  const H = 90
  const top = 16
  const fill = Math.min(1, backlog / TANK_MAX)
  const liquidH = fill * H
  const color = severity === 'CRIT' ? '#ef4444' : severity === 'WARN' ? '#f59e0b' : '#10b981'
  const thrY = top + H - (THRESHOLD / TANK_MAX) * H
  return (
    <div className="relative flex flex-col items-center">
      <svg width="94" height="126" viewBox="0 0 104 130">
        <defs>
          <clipPath id="tankBody">
            <rect x="14" y={top} width="76" height={H} />
          </clipPath>
        </defs>
        {/* 바닥/몸통 */}
        <ellipse cx="52" cy={top + H} rx="38" ry="8" fill="#0f172a" stroke="#475569" strokeWidth="2" />
        <rect x="14" y={top} width="76" height={H} fill="#0f172a" />
        {/* 액체 */}
        <g clipPath="url(#tankBody)">
          <motion.rect
            x="14"
            width="76"
            fill={color}
            fillOpacity={0.85}
            initial={false}
            animate={{ y: top + H - liquidH, height: liquidH + 12 }}
            transition={{ type: 'spring', stiffness: 90, damping: 18 }}
          />
          <motion.ellipse
            cx="52"
            rx="38"
            ry="6"
            fill={color}
            initial={false}
            animate={{ cy: top + H - liquidH }}
            transition={{ type: 'spring', stiffness: 90, damping: 18 }}
          />
        </g>
        <line x1="14" y1={top} x2="14" y2={top + H} stroke="#475569" strokeWidth="2" />
        <line x1="90" y1={top} x2="90" y2={top + H} stroke="#475569" strokeWidth="2" />
        <ellipse cx="52" cy={top} rx="38" ry="8" fill="#1e293b" fillOpacity="0.55" stroke="#64748b" strokeWidth="2" />
        {/* 임계치(1,000) 눈금 */}
        <line x1="8" y1={thrY} x2="96" y2={thrY} stroke="#f87171" strokeWidth="1.5" strokeDasharray="4 3" />
        <text x="98" y={thrY + 3} fontSize="9" fill="#f87171" fontFamily="monospace">
          1k
        </text>
      </svg>
      {severity === 'CRIT' && (
        <motion.div className="absolute -right-2 top-0 text-red-400" animate={{ opacity: [1, 0.1, 1] }} transition={{ duration: 0.6, repeat: Infinity }}>
          <AlertTriangle size={22} />
        </motion.div>
      )}
    </div>
  )
}

export default function PipelineTopology({ snap }: { snap: Snapshot }) {
  const { pipeline: p, queue: q, events } = snap
  const aiAlert = events.some((e) => ['VIBRATION_HIGH', 'BACKLOG_HIGH', 'NODE_DOWN', 'TEMP_HIGH'].includes(e))
  const aiAct = events.some((e) => e.startsWith('ACTION_'))
  const pct = Math.round(q.bottleneck_pct)
  const tankColor = q.severity === 'CRIT' ? 'text-red-400' : q.severity === 'WARN' ? 'text-amber-400' : 'text-emerald-400'
  const queueStatusText = q.severity === 'CRIT' ? '적체 위험 (CRITICAL)' : q.severity === 'WARN' ? '주의 (WARNING)' : '정상 (OK)'

  return (
    <section className="panel relative p-4">
      {/* ── 섹션 헤더 (이름 및 설명) ── */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500/20 text-sky-400">
            <Network size={17} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>SECTION 1 : 실시간 데이터 파이프라인 &amp; Pub/Sub 큐 토폴로지</span>
              <span className="rounded bg-sky-950 px-2 py-0.5 text-[10px] font-normal text-sky-300 border border-sky-800">
                Pipeline &amp; Queue Topology
              </span>
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex items-center gap-1.5 rounded-md bg-slate-800/80 px-2.5 py-1 text-slate-300 border border-slate-700">
            <span className="text-slate-400">큐 상태:</span>
            <span className={tankColor}>{queueStatusText}</span>
          </div>
          <div className="flex items-center gap-1.5 rounded-md bg-slate-800/80 px-2.5 py-1 text-slate-300 border border-slate-700">
            <span className="text-slate-400">전체 누적 적재:</span>
            <span className="text-emerald-300 font-bold">{q.rows_written.toLocaleString()} rows</span>
          </div>
        </div>
      </div>

      {/* ── 파이프라인 흐름 ── */}
      <div className="flex flex-wrap items-center justify-around gap-3 lg:flex-nowrap">
        {/* 1. Edge */}
        <Node
          icon={<Cpu size={26} />}
          name="Edge Gateway"
          subtext="현장 IoT 수집 장비"
          tone="sky"
          badge={`${Math.round(p.edge_rate)} msg/s`}
        />

        <Pipe rate={p.edge_rate} color="#38bdf8" label="MQTT/gRPC 전송" />

        {/* 2. Cloud Ingestion */}
        <Node
          icon={<Cloud size={26} />}
          name="Cloud Ingestion"
          subtext="GCP API 게이트웨이"
          tone="sky"
          badge={`${Math.round(p.route_a_rate)} msg/s`}
        />

        <Pipe rate={p.route_a_rate} color="#38bdf8" label="Pub/Sub 인입" />

        {/* 3. Pub/Sub 큐 탱크 */}
        <div className="flex flex-col items-center px-2 py-1 rounded-xl bg-slate-950/40 border border-slate-800 shrink-0">
          <span className="text-[11px] font-bold text-slate-300 mb-0.5">Pub/Sub 메시지 버퍼</span>
          <QueueTank backlog={q.backlog_count} severity={q.severity} />
          <div className={`mt-0.5 flex items-baseline gap-2 font-mono ${tankColor}`}>
            <motion.span
              key={q.severity}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
              className="text-xl font-bold tabular-nums"
            >
              {q.backlog_count.toLocaleString()}건
            </motion.span>
            <span className="text-[11px] font-semibold">({pct}%)</span>
          </div>
          <div className="mt-1 h-1.5 w-24 overflow-hidden rounded-full bg-slate-800">
            <motion.div
              className={q.severity === 'CRIT' ? 'bg-red-500' : q.severity === 'WARN' ? 'bg-amber-500' : 'bg-emerald-500'}
              style={{ height: '100%' }}
              animate={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        </div>

        {/* 4. Fan-out (BigQuery & AI Agent) */}
        <div className="flex flex-col gap-4 border-l-2 border-slate-700/80 py-1 pl-3 shrink-0">
          {/* BigQuery 분기 */}
          <div className="flex items-center gap-2">
            <Pipe rate={p.bq_rate} color="#34d399" label="배치 스트리밍" />
            <Node
              icon={<Database size={24} />}
              name="BigQuery DWH"
              subtext="데이터웨어하우스"
              tone="emerald"
              badge={`${q.rows_written.toLocaleString()}건`}
              badgePrefix="적재: "
            />
          </div>
          {/* AI Agent 분기 */}
          <div className="flex items-center gap-2">
            <Pipe rate={aiAlert ? Math.max(p.route_b_rate, 6) : 0} color="#f87171" label="이상 탐지 텔레메트리" />
            <Node
              icon={<Bot size={24} />}
              name="AIOps 치유 엔진"
              subtext={aiAct ? '자율 치유 액션 중' : aiAlert ? '이상 이벤트 감지' : '실시간 모니터링'}
              tone={aiAct ? 'violet' : aiAlert ? 'red' : 'slate'}
              pulse={aiAlert && !aiAct}
              badge={aiAct ? 'ACTING' : aiAlert ? 'ALERT' : 'MONITORING'}
            />
          </div>
        </div>
      </div>
    </section>
  )
}
