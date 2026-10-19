import { AnimatePresence, motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { ArrowRight, BookOpen, Bell, Bot, Container, Hash, MessageSquare, ShieldCheck, Sparkles, TrendingUp, Wrench, X } from 'lucide-react'
import type { Snapshot } from '../types'

function Card({
  title,
  actionNo,
  subtext,
  icon,
  active,
  tone,
  children,
}: {
  title: string
  actionNo: string
  subtext: string
  icon: ReactNode
  active: boolean
  tone: string
  children: ReactNode
}) {
  return (
    <motion.div
      animate={{ opacity: active ? 1 : 0.7 }}
      className={`relative flex min-h-[220px] flex-col rounded-xl border-2 bg-slate-900/90 p-4 transition-colors ${active ? tone : 'border-slate-700'}`}
    >
      {/* 카드 헤더 */}
      <div className="mb-3 flex items-start justify-between border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="text-slate-400">{icon}</div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[10px] font-bold text-sky-400 bg-sky-950 px-1.5 py-0.5 rounded border border-sky-800">
                {actionNo}
              </span>
              <h3 className="text-xs font-bold text-slate-200">{title}</h3>
            </div>
            <p className="text-[10px] text-slate-400">{subtext}</p>
          </div>
        </div>
        <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-semibold ${
          active ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
        }`}>
          {active ? 'RUNNING' : 'IDLE'}
        </span>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center">{children}</div>
    </motion.div>
  )
}

/** 위젯 1 — Slack RAG 미니 카드 (Action 1) */
function SlackWidget({ snap }: { snap: Snapshot }) {
  const card = snap.remediation.slack
  return (
    <Card
      actionNo="ACTION 1"
      title="Slack 알림 &amp; SOP RAG"
      subtext="진동 이상 시 정비 매뉴얼 자동 추천"
      icon={<MessageSquare size={18} />}
      active={!!card}
      tone="border-violet-500 shadow-lg shadow-violet-500/10"
    >
      <AnimatePresence mode="wait">
        {card ? (
          <motion.div
            key={card.ts}
            initial={{ y: 20, opacity: 0, scale: 0.9 }}
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
                  매뉴얼 참조 p.{card.manual_page}
                </span>
                <span className="flex items-center gap-1.5 text-sm font-extrabold text-amber-300">
                  <motion.span animate={{ rotate: [0, -25, 0] }} transition={{ duration: 1.2, repeat: Infinity }}>
                    <Wrench size={16} />
                  </motion.span>
                  {card.key_action}
                </span>
                <div className="flex items-center gap-2">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-slate-700">
                    <div className="h-full bg-emerald-400" style={{ width: `${Math.round(card.confidence * 100)}%` }} />
                  </div>
                  <span className="font-mono text-[10px] text-emerald-400">
                    신뢰도 {Math.round(card.confidence * 100)}%
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center px-3 py-2 text-slate-500">
            <Bot size={34} className="opacity-40" />
            <span className="text-xs font-medium text-slate-400">모니터링 대기 중</span>
            <p className="text-[11px] leading-tight text-slate-500">
              모터 진동 이상 감지 시 엔지니어 채널로 정비 가이드가 자동 발송됩니다.
            </p>
          </div>
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

/** 위젯 2 — Container Scale-up 미터기 (Action 2) */
function ScaleWidget({ snap }: { snap: Snapshot }) {
  const sc = snap.remediation.scale
  const active = snap.worker_pods.filter((p) => p.status === 'ACTIVE').length
  const starting = snap.worker_pods.filter((p) => p.status === 'STARTING').length
  const pct = snap.queue.throughput_pct

  return (
    <Card
      actionNo="ACTION 2"
      title="GKE 컨테이너 오토스케일"
      subtext="Pub/Sub 큐 적체 시 파드 동적 확장"
      icon={<Container size={18} />}
      active={!!sc}
      tone="border-sky-500 shadow-lg shadow-sky-500/10"
    >
      {sc ? (
        <div className="flex flex-col items-center gap-2.5 w-full">
          <div className="flex items-center justify-between w-full px-2 text-[11px] text-slate-400">
            <span>이전 파드: <b className="text-slate-200 font-mono">{sc.from_pods}개</b></span>
            <span>확장 파드: <b className="text-sky-300 font-mono">{active + starting}개</b></span>
          </div>

          <div className="flex flex-col items-center gap-1.5 bg-slate-950/60 p-2 rounded-lg border border-slate-800 w-full">
            <PodRow filled={sc ? sc.from_pods : active} tone="border-slate-400 bg-slate-500/60" />
            <ArrowRight size={15} className="rotate-90 text-sky-400" />
            <PodRow filled={sc ? active + starting : active} tone={starting ? 'border-sky-400 bg-sky-400/70' : 'border-emerald-400 bg-emerald-400/70'} />
          </div>

          <div className="flex items-center justify-between w-full px-1">
            <span className="text-[11px] text-slate-400">처리량 증대율:</span>
            <motion.div key={pct} initial={{ scale: 1.25 }} animate={{ scale: 1 }} className={`flex items-center gap-1 font-mono text-base font-extrabold ${pct > 100 ? 'text-emerald-300' : 'text-slate-400'}`}>
              +{pct}%
              {pct > 100 && (
                <motion.span animate={{ y: [2, -2, 2] }} transition={{ duration: 0.7, repeat: Infinity }}>
                  <TrendingUp size={16} />
                </motion.span>
              )}
            </motion.div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-center px-3 py-2 text-slate-500">
          <Container size={34} className="opacity-40" />
          <span className="text-xs font-medium text-slate-400">큐 처리량 정상 (스케일 대기)</span>
          <p className="text-[11px] leading-tight text-slate-500">
            메시지 큐 적체율 급증 시 파드를 즉각 확장하여 병목을 선제 해소합니다.
          </p>
        </div>
      )}
    </Card>
  )
}

/** 위젯 3 — Failover 스위치 보드 (Action 3): 철도 분기점 + 0% Data Loss 방패 */
function FailoverWidget({ snap }: { snap: Snapshot }) {
  const fo = snap.remediation.failover
  const done = fo?.status === 'DONE'
  const aPath = 'M20 40 H70 H120'
  const bPath = 'M20 40 H60 C 80 40, 90 80, 110 80 H120'

  return (
    <Card
      actionNo="ACTION 3"
      title="콜드체인 무중단 Failover"
      subtext="과온 감지 시 예비 존으로 우회 라우팅"
      icon={<ArrowRight size={18} />}
      active={!!fo}
      tone="border-emerald-500 shadow-lg shadow-emerald-500/10"
    >
      <div className="flex w-full flex-col items-center gap-2">
        <svg viewBox="0 0 220 100" className="w-full max-w-[240px]">
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
            <rect x="120" y="22" width="84" height="34" rx="8" fill="#0f172a" stroke={done ? '#ef4444' : '#38bdf8'} strokeWidth="2.5" opacity={done ? 0.6 : 1} />
            <text x="135" y="44" fontSize="11" fontWeight="700" fill="#cbd5e1" fontFamily="sans-serif">Zone A</text>
            {done && (
              <g stroke="#ef4444" strokeWidth="3" strokeLinecap="round">
                <line x1="180" y1="32" x2="194" y2="46" />
                <line x1="194" y1="32" x2="180" y2="46" />
              </g>
            )}
          </g>
          {/* Zone B */}
          <g>
            <rect x="120" y="60" width="84" height="34" rx="8" fill="#0f172a" stroke={done ? '#34d399' : '#475569'} strokeWidth="2.5" />
            <text x="135" y="82" fontSize="11" fontWeight="700" fill="#cbd5e1" fontFamily="sans-serif">Zone B</text>
            <circle cx="188" cy="77" r="5" fill={done ? '#34d399' : '#475569'} />
          </g>
        </svg>

        {fo ? (
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-slate-400 text-[11px]">결과:</span>
            <div className={`flex items-center gap-1 rounded-md px-2 py-0.5 font-bold ${done ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/20 text-red-300'}`}>
              {done ? <ShieldCheck size={15} /> : <X size={15} />}
              <span>데이터 손실 {fo.data_loss_pct}% (무손실 보장)</span>
            </div>
          </div>
        ) : (
          <span className="text-[11px] text-slate-500">Zone A 정상 라우팅 중 (절체 대기)</span>
        )}
      </div>
    </Card>
  )
}

export default function RemediationVisualDock({ snap }: { snap: Snapshot }) {
  const activeActionsCount = [snap.remediation.slack, snap.remediation.scale, snap.remediation.failover].filter(Boolean).length

  return (
    <section className="panel relative flex flex-col gap-3 p-4">
      {/* ── 섹션 헤더 ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-500/20 text-violet-400">
            <Sparkles size={18} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>SECTION 4 : AIOps 실시간 자율 치유 및 조치 현황</span>
              <span className="rounded bg-violet-950 px-2 py-0.5 text-[10px] font-normal text-violet-300 border border-violet-800">
                Autonomous Remediation Dock
              </span>
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className={`rounded px-2.5 py-0.5 ${
            activeActionsCount > 0
              ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40 font-bold'
              : 'bg-slate-800 text-slate-400 border border-slate-700'
          }`}>
            {activeActionsCount > 0 ? `자율 치유 액션 가동 중 (${activeActionsCount}/3)` : '모든 치유 액션 대기 중 (정상)'}
          </span>
        </div>
      </div>

      {/* ── 액션 카드 3종 그리드 ── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <SlackWidget snap={snap} />
        <ScaleWidget snap={snap} />
        <FailoverWidget snap={snap} />
      </div>
    </section>
  )
}
