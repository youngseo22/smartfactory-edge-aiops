import { AnimatePresence, motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { ArrowRight, BookOpen, Bell, Bot, Container, Hash, MessageSquare, ShieldCheck, TrendingUp, Wrench, X } from 'lucide-react'
import type { Snapshot } from '../types'

function Card({ icon, active, tone, children }: { icon: ReactNode; active: boolean; tone: string; children: ReactNode }) {
  return (
    <motion.div
      animate={{ opacity: active ? 1 : 0.5 }}
      className={`relative flex min-h-[170px] flex-col gap-3 rounded-xl border-2 bg-slate-900/90 p-4 transition-colors ${active ? tone : 'border-slate-700'}`}
    >
      <div className="text-slate-400">{icon}</div>
      <div className="flex flex-1 items-center justify-center">{children}</div>
    </motion.div>
  )
}

/** 위젯 1 — Slack RAG 미니 카드 (Action A) */
function SlackWidget({ snap }: { snap: Snapshot }) {
  const card = snap.remediation.slack
  return (
    <Card icon={<MessageSquare size={20} />} active={!!card} tone="border-violet-500 shadow-lg shadow-violet-500/10">
      <AnimatePresence mode="wait">
        {card ? (
          <motion.div
            key={card.ts}
            initial={{ y: 30, opacity: 0, scale: 0.85 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            className="w-full overflow-hidden rounded-lg border border-slate-600 bg-slate-800 shadow-xl"
          >
            <div className="flex items-center justify-between bg-[#4A154B] px-2.5 py-1.5 text-white">
              <span className="flex items-center gap-1 text-xs font-bold">
                <Hash size={13} />
                {card.channel.replace('#', '')}
              </span>
              <motion.span animate={{ rotate: [0, -18, 18, -12, 12, 0] }} transition={{ duration: 0.8, repeat: Infinity, repeatDelay: 1.5 }}>
                <Bell size={14} />
              </motion.span>
            </div>
            <div className="flex gap-2.5 p-2.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-violet-600 text-white">
                <Bot size={20} />
              </div>
              <div className="flex min-w-0 flex-col gap-1.5">
                <span className="flex w-fit items-center gap-1 rounded bg-sky-500/20 px-1.5 py-0.5 text-[11px] font-semibold text-sky-300">
                  <BookOpen size={12} />
                  Manual p.{card.manual_page}
                </span>
                <span className="flex items-center gap-1.5 text-base font-extrabold text-amber-300">
                  <motion.span animate={{ rotate: [0, -25, 0] }} transition={{ duration: 1.2, repeat: Infinity }}>
                    <Wrench size={18} />
                  </motion.span>
                  {card.key_action}
                </span>
                <div className="h-1 overflow-hidden rounded-full bg-slate-700">
                  <div className="h-full bg-emerald-400" style={{ width: `${Math.round(card.confidence * 100)}%` }} />
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <Bot key="idle" size={40} className="text-slate-700" />
        )}
      </AnimatePresence>
    </Card>
  )
}

function PodRow({ filled, total = 6, tone }: { filled: number; total?: number; tone: string }) {
  return (
    <div className="flex gap-1.5">
      {Array.from({ length: total }).map((_, i) => (
        <motion.span
          key={`${i}-${i < filled}`}
          initial={i < filled ? { scale: 0.4 } : false}
          animate={{ scale: 1 }}
          className={`h-5 w-5 rounded-[5px] border-2 ${i < filled ? tone : 'border-slate-600 bg-transparent'}`}
        />
      ))}
    </div>
  )
}

/** 위젯 2 — Container Scale-up 미터기 (Action B) */
function ScaleWidget({ snap }: { snap: Snapshot }) {
  const sc = snap.remediation.scale
  const active = snap.worker_pods.filter((p) => p.status === 'ACTIVE').length
  const starting = snap.worker_pods.filter((p) => p.status === 'STARTING').length
  const pct = snap.queue.throughput_pct
  return (
    <Card icon={<Container size={20} />} active={!!sc} tone="border-sky-500 shadow-lg shadow-sky-500/10">
      <div className="flex flex-col items-center gap-3">
        <PodRow filled={sc ? sc.from_pods : active} tone="border-slate-400 bg-slate-500/60" />
        <ArrowRight size={18} className="rotate-90 text-sky-300" />
        <PodRow filled={sc ? active + starting : active} tone={starting ? 'border-sky-400 bg-sky-400/70' : 'border-emerald-400 bg-emerald-400/70'} />
        <motion.div key={pct} initial={{ scale: 1.25 }} animate={{ scale: 1 }} className={`flex items-center gap-1 font-mono text-xl font-extrabold ${pct > 100 ? 'text-emerald-300' : 'text-slate-500'}`}>
          {pct}%
          {pct > 100 && (
            <motion.span animate={{ y: [3, -3, 3] }} transition={{ duration: 0.7, repeat: Infinity }}>
              <TrendingUp size={20} />
            </motion.span>
          )}
        </motion.div>
      </div>
    </Card>
  )
}

/** 위젯 3 — Failover 스위치 보드 (Action C): 철도 분기점 + 0% Data Loss 방패 */
function FailoverWidget({ snap }: { snap: Snapshot }) {
  const fo = snap.remediation.failover
  const done = fo?.status === 'DONE'
  const aPath = 'M20 40 H70 H120'
  const bPath = 'M20 40 H60 C 80 40, 90 80, 110 80 H120'
  return (
    <Card icon={<ArrowRight size={20} />} active={!!fo} tone="border-emerald-500 shadow-lg shadow-emerald-500/10">
      <div className="flex w-full flex-col items-center gap-2">
        <svg viewBox="0 0 220 110" className="w-full max-w-[250px]">
          {/* 선로 */}
          <path d={aPath} stroke="#334155" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d={bPath} stroke="#334155" strokeWidth="6" fill="none" strokeLinecap="round" />
          <path d={done ? bPath : aPath} stroke={done ? '#34d399' : '#38bdf8'} strokeWidth="6" fill="none" strokeLinecap="round" strokeDasharray="10 8" style={{ filter: `drop-shadow(0 0 5px ${done ? '#34d399' : '#38bdf8'})` }}>
            <animate attributeName="stroke-dashoffset" from="0" to="-36" dur="0.8s" repeatCount="indefinite" />
          </path>
          {/* 분기점 */}
          <circle cx="60" cy="40" r="6" fill="#0f172a" stroke={done ? '#34d399' : '#38bdf8'} strokeWidth="3" />
          {/* 달리는 신호 */}
          <circle r="5" fill={done ? '#6ee7b7' : '#7dd3fc'}>
            <animateMotion dur="1.6s" repeatCount="indefinite" path={done ? bPath : aPath} />
          </circle>
          {/* Zone A */}
          <g>
            <rect x="120" y="22" width="84" height="36" rx="8" fill="#0f172a" stroke={done ? '#ef4444' : '#38bdf8'} strokeWidth="2.5" opacity={done ? 0.6 : 1} />
            <text x="150" y="45" fontSize="13" fontWeight="700" fill="#cbd5e1" fontFamily="monospace">A</text>
            {done && (
              <g stroke="#ef4444" strokeWidth="3.5" strokeLinecap="round">
                <line x1="176" y1="32" x2="192" y2="48" />
                <line x1="192" y1="32" x2="176" y2="48" />
              </g>
            )}
          </g>
          {/* Zone B */}
          <g>
            <rect x="120" y="62" width="84" height="36" rx="8" fill="#0f172a" stroke={done ? '#34d399' : '#475569'} strokeWidth="2.5" />
            <text x="150" y="85" fontSize="13" fontWeight="700" fill="#cbd5e1" fontFamily="monospace">B</text>
            <circle cx="186" cy="80" r="6" fill={done ? '#34d399' : '#475569'} />
          </g>
        </svg>
        <AnimatePresence>
          {fo && (
            <motion.div
              initial={{ scale: 0, rotate: -20 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 15 }}
              className={`flex items-center gap-1.5 rounded-lg border-2 px-2.5 py-1 font-mono text-sm font-bold ${done ? 'border-emerald-500 bg-emerald-500/15 text-emerald-300' : 'border-red-500 bg-red-500/15 text-red-300'}`}
            >
              {done ? <ShieldCheck size={18} /> : <X size={18} />}
              {fo.data_loss_pct}%
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  )
}

export default function RemediationVisualDock({ snap }: { snap: Snapshot }) {
  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <SlackWidget snap={snap} />
      <ScaleWidget snap={snap} />
      <FailoverWidget snap={snap} />
    </section>
  )
}
