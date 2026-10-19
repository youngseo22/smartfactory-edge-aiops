import { motion } from 'framer-motion'
import { ShieldCheck, Snowflake, WifiOff } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { Snapshot, ZoneState } from '../types'

const TEMP_THRESHOLD = 8.0

function ZoneBox({ zone, label, serving, failover }: { zone: ZoneState; label: string; serving: boolean; failover: boolean }) {
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
  return (
    <motion.div
      animate={{ opacity: off ? 0.55 : 1, filter: off ? 'grayscale(0.8)' : 'grayscale(0)' }}
      className={`relative flex w-32 flex-col items-center gap-1 rounded-lg border-2 bg-slate-950/70 p-2 ${border}`}
    >
      <div className="flex w-full items-center justify-between">
        <span className="font-mono text-xs">{label}</span>
        <span className={`h-2.5 w-2.5 rounded-full ${led} ${off || warn ? 'animate-blink' : ''}`} />
      </div>
      {off ? <WifiOff size={30} className="text-red-400" /> : <Snowflake size={30} />}
      <span className="font-mono text-lg font-bold tabular-nums">{zone.temp_c !== null ? `${zone.temp_c.toFixed(1)}°` : '--'}</span>
      {standby && !failover && <span className="absolute -bottom-2 rounded bg-slate-800 px-1.5 font-mono text-[9px] text-slate-400">STANDBY</span>}
      {serving && failover && <span className="absolute -bottom-2 rounded bg-emerald-600 px-1.5 font-mono text-[9px] text-white">ON</span>}
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
      <div className="h-52 rounded-lg border-2 border-slate-700 bg-slate-950/60 p-2">
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
              tickFormatter={(v: number) => `${v}s`}
              stroke="#475569"
              tick={{ fontSize: 10, fill: '#64748b' }}
              allowDataOverflow
            />
            <YAxis domain={[0, 15]} ticks={[0, 5, 10, 15]} tickFormatter={(v: number) => `${v}°`} stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
            <ReferenceLine y={TEMP_THRESHOLD} stroke="#ef4444" strokeDasharray="6 4" strokeWidth={2} />
            <Area type="monotone" dataKey="a" stroke="#38bdf8" strokeWidth={2.5} fill="url(#gA)" isAnimationActive={false} connectNulls={false} dot={false} />
            <Area type="monotone" dataKey="b" stroke="#34d399" strokeWidth={2.5} fill="url(#gB)" isAnimationActive={false} connectNulls={false} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Zone A → Zone B 컨테이너 맵 */}
      <div className="flex items-center justify-center gap-2 pb-2">
        {zoneA && <ZoneBox zone={zoneA} label="A" serving={aServing} failover={failover} />}

        <svg viewBox="0 0 120 44" className="h-11 w-32 shrink-0">
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

        {zoneB && <ZoneBox zone={zoneB} label="B" serving={!aServing} failover={failover} />}

        {failover && (
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="ml-1 flex items-center gap-1 rounded-lg border-2 border-emerald-500 bg-emerald-500/15 px-2 py-1 font-mono text-sm font-bold text-emerald-300">
            <ShieldCheck size={18} />
            {routing.data_loss_pct}%
          </motion.div>
        )}
      </div>
    </section>
  )
}
