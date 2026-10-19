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
    ? '통신 오프라인'
    : warn
      ? '온도 과열 경보'
      : serving
        ? '정상 서빙'
        : '예비 대기'

  return (
    <motion.div
      animate={{ opacity: off ? 0.6 : 1, filter: off ? 'grayscale(0.8)' : 'grayscale(0)' }}
      className={`relative flex flex-1 min-w-[105px] max-w-[145px] flex-col items-center gap-1 rounded-lg border-2 bg-slate-950/80 p-2.5 ${border}`}
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-slate-200">Zone {label}</span>
          <span className="text-[10px] text-slate-400">{name}</span>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${led} ${off || warn ? 'animate-blink' : ''}`} />
      </div>

      <div className="my-0.5">
        {off ? <WifiOff size={26} className="text-red-400" /> : <Snowflake size={26} />}
      </div>

      <div className="flex flex-col items-center">
        <span className="font-mono text-xl font-bold tabular-nums">
          {zone.temp_c !== null ? `${zone.temp_c.toFixed(1)}°C` : '--'}
        </span>
        <span className="text-[10px] font-medium text-slate-300">
          {statusKorean}
        </span>
      </div>

      <div className="mt-0.5 w-full text-center">
        {standby && !failover && (
          <span className="inline-block rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[9px] text-slate-400 border border-slate-700">
            대기 (STANDBY)
          </span>
        )}
        {serving && failover && (
          <span className="inline-block rounded bg-emerald-600 px-1.5 py-0.5 font-mono text-[9px] font-bold text-white shadow-sm">
            절체 (ACTIVE)
          </span>
        )}
        {serving && !failover && (
          <span className="inline-block rounded bg-emerald-950/80 px-1.5 py-0.5 font-mono text-[9px] font-semibold text-emerald-400 border border-emerald-700/60">
            주 가동 (MAIN)
          </span>
        )}
      </div>
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
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-1.5 text-xs text-slate-300">
          <span className="font-bold text-slate-200">이중화 보관존 실시간 트래픽 라우팅</span>
          <span
            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold border ${
              failover
                ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-300'
                : 'border-slate-700 bg-slate-900 text-slate-300'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${failover ? 'bg-emerald-400 animate-pulse' : 'bg-sky-400'}`} />
            {failover ? 'Zone B 트래픽 우회 절체 가동' : 'Zone A 정상 인입 중'}
          </span>
        </div>

        <div className="flex items-center justify-between gap-2 py-1">
          {zoneA && <ZoneBox zone={zoneA} label="A" name="메인 냉장실" serving={aServing} failover={failover} />}

          {/* 절체 흐름 화살표 */}
          <div className="flex flex-1 flex-col items-center justify-center min-w-[70px] max-w-[110px]">
            <span className={`text-[9px] font-mono mb-1 font-semibold ${failover ? 'text-emerald-300' : 'text-slate-400'}`}>
              {failover ? '자동 절체 가동' : '라우팅 대기'}
            </span>
            <svg viewBox="0 0 100 36" className="h-8 w-full shrink-0">
              <path d="M4 18 C 30 18, 70 18, 92 18" stroke="#334155" strokeWidth="3" fill="none" strokeLinecap="round" />
              {failover ? (
                <>
                  <motion.path
                    d="M4 18 C 30 18, 70 18, 92 18"
                    stroke="#34d399"
                    strokeWidth="3.5"
                    fill="none"
                    strokeLinecap="round"
                    strokeDasharray="8 6"
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1, strokeDashoffset: [0, -28] }}
                    transition={{
                      pathLength: { duration: 0.6 },
                      opacity: { duration: 0.3 },
                      strokeDashoffset: { duration: 0.8, repeat: Infinity, ease: 'linear' },
                    }}
                    style={{ filter: 'drop-shadow(0 0 6px #34d399)' }}
                  />
                  <polygon points="86,10 98,18 86,26" fill="#34d399" style={{ filter: 'drop-shadow(0 0 6px #34d399)' }} />
                </>
              ) : (
                <polygon points="86,12 96,18 86,24" fill="#475569" />
              )}
            </svg>
          </div>

          {zoneB && <ZoneBox zone={zoneB} label="B" name="예비 냉장실" serving={!aServing} failover={failover} />}
        </div>

        {/* 절체 가동 시 하단 데이터 무손실 방어 배너 */}
        {failover && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
            className="mt-2.5 flex items-center justify-between rounded-md border border-emerald-500/40 bg-emerald-950/40 px-3 py-1.5 text-xs text-emerald-300"
          >
            <div className="flex items-center gap-1.5 font-semibold">
              <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
              <span className="text-[11px]">무손실 절체 방어 (Zero Data Loss)</span>
            </div>
            <span className="font-mono text-[11px] font-bold text-emerald-200">
              손실률 {routing.data_loss_pct}%
            </span>
          </motion.div>
        )}
      </div>
    </section>
  )
}
