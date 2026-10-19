import { motion } from 'framer-motion'
import { ShieldCheck, Snowflake, WifiOff } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { Snapshot, ZoneState } from '../types'

const TEMP_THRESHOLD = 8.0

function ZoneBox({
  zone,
  label,
  name,
  serving,
  failover,
}: {
  zone: ZoneState
  label: string
  name: string
  serving: boolean
  failover: boolean
}) {
  const off = zone.status === 'OFFLINE'
  const warn = zone.status === 'WARNING'
  const standby = !serving && !off
  const led = off ? 'bg-red-500' : warn ? 'bg-amber-400' : 'bg-emerald-400'
  const border = off
    ? 'border-red-600/70 text-slate-500'
    : warn
      ? 'border-amber-500 text-amber-300'
      : serving
        ? 'border-emerald-500 text-emerald-300'
        : 'border-slate-600 text-slate-400'

  const statusKorean = off
    ? '센서 통신 오프라인'
    : warn
      ? '온도 과열 경보'
      : serving
        ? '정상 서빙 중'
        : '예비 대기'

  return (
    <motion.div
      animate={{ opacity: off ? 0.6 : 1, filter: off ? 'grayscale(0.8)' : 'grayscale(0)' }}
      className={`relative flex w-36 flex-col items-center gap-1.5 rounded-lg border-2 bg-slate-950/80 p-2.5 ${border}`}
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-slate-200">Zone {label}</span>
          <span className="text-[10px] text-slate-400">{name}</span>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${led} ${off || warn ? 'animate-blink' : ''}`} />
      </div>

      <div className="my-1">
        {off ? <WifiOff size={28} className="text-red-400" /> : <Snowflake size={28} />}
      </div>

      <div className="flex flex-col items-center">
        <span className="font-mono text-xl font-bold tabular-nums">
          {zone.temp_c !== null ? `${zone.temp_c.toFixed(1)}°C` : '--'}
        </span>
        <span className="text-[10px] font-medium text-slate-300 mt-0.5">
          {statusKorean}
        </span>
      </div>

      {standby && !failover && (
        <span className="absolute -bottom-2.5 rounded bg-slate-800 px-2 py-0.5 font-mono text-[9px] text-slate-300 border border-slate-700">
          대기 (STANDBY)
        </span>
      )}
      {serving && failover && (
        <span className="absolute -bottom-2.5 rounded bg-emerald-600 px-2 py-0.5 font-mono text-[9px] font-bold text-white shadow-md">
          절체 가동 (ACTIVE)
        </span>
      )}
    </motion.div>
  )
}

export default function ColdChainGraphView({ snap }: { snap: Snapshot }) {
  const { routing, zones } = snap
  const data = snap.temp_history.map((p) => ({
    sec: Math.round(((p.ts - snap.ts) / 1000) * 10) / 10,
    a: p.temp_a,
    b: p.temp_b,
  }))
  const failover = routing.failover_active
  const zoneA = zones['ZONE_A']
  const zoneB = zones['ZONE_B']
  const aServing = routing.active_zone === 'ZONE_A'

  return (
    <section className="panel panel-rivets relative flex flex-col gap-3 p-4">
      {/* ── 섹션 헤더 ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-sky-500/20 text-sky-400">
            <Snowflake size={18} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>SECTION 3 : 스마트 콜드체인 실시간 온도</span>
              <span className="rounded bg-sky-950 px-2 py-0.5 text-[10px] font-normal text-sky-300 border border-sky-800">
                Cold Chain Dual-Zone
              </span>
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className={`rounded px-2 py-0.5 ${failover ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold' : 'bg-slate-800 text-slate-300 border border-slate-700'}`}>
            {failover ? 'Zone B 자동 절체 운용 중' : 'Zone A 정상 공급 중'}
          </span>
        </div>
      </div>

      {/* ── 실시간 온도 그래프 + 범례 ── */}
      <div className="rounded-lg border-2 border-slate-700 bg-slate-950/60 p-2.5">
        {/* 그래프 범례 상단 바 */}
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-1.5 px-1 text-xs">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-sky-400" />
              <span className="font-medium text-slate-300">Zone A (주 보관소)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span className="font-medium text-slate-300">Zone B (예비 보관소)</span>
            </div>
            <div className="flex items-center gap-1.5 text-red-400">
              <span className="h-0.5 w-3.5 border-t-2 border-dashed border-red-500" />
              <span className="text-[11px] font-semibold">관리 기준선 (8.0°C)</span>
            </div>
          </div>
          <span className="font-mono text-[10px] text-slate-400">단위: 최근 30초 / 섭씨(°C)</span>
        </div>

        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
              <defs>
                <linearGradient id="gA" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gB" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#34d399" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis
                dataKey="sec"
                type="number"
                domain={[-30, 0]}
                ticks={[-30, -20, -10, 0]}
                tickFormatter={(v: number) => `${v}초`}
                stroke="#475569"
                tick={{ fontSize: 10, fill: '#64748b' }}
                allowDataOverflow
              />
              <YAxis domain={[0, 15]} ticks={[0, 5, 8, 10, 15]} tickFormatter={(v: number) => `${v}°`} stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
              <ReferenceLine y={TEMP_THRESHOLD} stroke="#ef4444" strokeDasharray="6 4" strokeWidth={2} />
              <Area type="monotone" dataKey="a" stroke="#38bdf8" strokeWidth={2.5} fill="url(#gA)" isAnimationActive={false} connectNulls={false} dot={false} />
              <Area type="monotone" dataKey="b" stroke="#34d399" strokeWidth={2.5} fill="url(#gB)" isAnimationActive={false} connectNulls={false} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Zone A → Zone B 라우팅 및 절체 현황 ── */}
      <div className="rounded-lg border-2 border-slate-700 bg-slate-950/60 p-3">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-300">
          <span className="font-semibold">이중화 보관존 실시간 트래픽 라우팅</span>
          <span className="text-[11px] text-slate-400">
            {failover ? '이상 감지로 인해 Zone B로 트래픽 우회 절체됨' : 'Zone A 정상 인입 중'}
          </span>
        </div>

        <div className="flex items-center justify-center gap-3 py-1">
          {zoneA && <ZoneBox zone={zoneA} label="A" name="메인 냉장실" serving={aServing} failover={failover} />}

          {/* 절체 흐름 화살표 */}
          <div className="flex flex-col items-center">
            <span className="text-[9px] font-mono text-slate-400 mb-0.5">
              {failover ? '자동 절체 가동' : '라우팅 대기'}
            </span>
            <svg viewBox="0 0 120 44" className="h-10 w-28 shrink-0">
              <path d="M4 22 C 40 22, 80 22, 112 22" stroke="#334155" strokeWidth="4" fill="none" strokeLinecap="round" />
              {failover && (
                <>
                  <motion.path
                    d="M4 22 C 40 22, 80 22, 112 22"
                    stroke="#34d399"
                    strokeWidth="4"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray="10 8"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1, strokeDashoffset: [0, -36] }}
                    transition={{ pathLength: { duration: 0.6 }, opacity: { duration: 0.3 }, strokeDashoffset: { duration: 0.8, repeat: Infinity, ease: 'linear' } }}
                    style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}
                  />
                  <polygon points="104,12 120,22 104,32" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }} />
                </>
              )}
            </svg>
          </div>

          {zoneB && <ZoneBox zone={zoneB} label="B" name="예비 냉장실" serving={!aServing} failover={failover} />}

          {failover && (
            <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-2 flex flex-col items-center justify-center rounded-lg border-2 border-emerald-500 bg-emerald-500/15 px-2.5 py-1.5 text-center">
              <div className="flex items-center gap-1 font-mono text-sm font-bold text-emerald-300">
                <ShieldCheck size={18} />
                <span>손실 {routing.data_loss_pct}%</span>
              </div>
              <span className="text-[9px] text-emerald-400 font-medium">데이터 무손실 방어</span>
            </motion.div>
          )}
        </div>
      </div>
    </section>
  )
}
