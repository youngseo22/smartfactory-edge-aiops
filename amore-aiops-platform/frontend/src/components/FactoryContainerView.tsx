import { motion } from 'framer-motion'
import { AlertTriangle, ArrowUp, Container, Cog, Zap } from 'lucide-react'
import { stepMotorSvm } from '../hooks/useDashboard'
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
            : pod.status === 'TERMINATING'
              ? ['0 0 0 0 rgba(245,158,11,0.8)', '0 0 14px 2px rgba(245,158,11,0.0)']
              : ['0 0 0 0 rgba(56,189,248,0.8)', '0 0 18px 4px rgba(56,189,248,0.0)'],
      }}
      transition={{ duration: 0.6 }}
      className={`relative flex flex-col items-center gap-1.5 rounded-lg border-2 px-2.5 pb-2 pt-2 ${style}`}
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
        <motion.div animate={{ scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] }} transition={{ duration: 0.5, repeat: Infinity }}>
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
      <span className="font-mono text-[10px] text-slate-400">
        {pod.status === 'ACTIVE'
          ? `부하 ${Math.round(pod.load_pct)}%`
          : pod.status === 'STARTING'
            ? '프로비저닝'
            : pod.status === 'TERMINATING'
              ? '종료 드레인'
              : 'Standby'}
      </span>
    </motion.div>
  )
}

export default function FactoryContainerView({ snap }: { snap: Snapshot }) {
  const { motor, worker_pods: pods } = snap
  const isMotorFault = snap.active_scenarios.includes(1) || snap.events.includes('VIBRATION_HIGH') || motor.svm >= SVM_WARN
  const isLineVibration = snap.active_scenarios.includes(6) || snap.events.includes('CONVEYOR_ANOMALY')

  // 모터 애니메이션 속도
  const spinDur = isMotorFault ? 1.0 : 3.2

  // 컨베이어 벨트 및 용기 상태:
  // 1) 모터 결함 시: 불량품 양산 방지를 위한 공정 안전 인터록 (라인 정지)
  // 2) 라인 진동 시: 인버터 이상으로 인한 비정상 급가속 (2.8 m/s) 및 흔들림
  // 3) 정상 시: 정속 이송 (1.0 m/s)
  const isConveyorHalt = isMotorFault
  const beltCls = isConveyorHalt ? '' : isLineVibration ? 'animate-belt-fast' : 'animate-belt'
  const bottleDur = isConveyorHalt ? 999999 : isLineVibration ? 2.5 : 6

  const activeCount = pods.filter((p) => p.status === 'ACTIVE').length
  const startingCount = pods.filter((p) => p.status === 'STARTING').length
  const terminatingCount = pods.filter((p) => p.status === 'TERMINATING').length

  return (
    <section className="panel panel-rivets relative flex flex-col gap-3 p-4">
      {/* ── 섹션 헤더 ── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500/20 text-amber-400">
            <Cog size={18} />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>SECTION 2 : 스마트 제조 라인 &amp; 처리 컨테이너</span>
              <span className="rounded bg-amber-950 px-2 py-0.5 text-[10px] font-normal text-amber-300 border border-amber-800">
                Assembly Line &amp; Worker Pods
              </span>
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className={`rounded px-2 py-0.5 ${isMotorFault ? 'bg-red-500/20 text-red-400 border border-red-500/40 font-bold' : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'}`}>
            {isMotorFault ? '모터 진동 경보 (ANOMALY)' : '모터 정상 작동 (NORMAL)'}
          </span>
        </div>
      </div>

      {/* ── 모터 + 계기판 ── */}
      <div className="relative flex items-center justify-around rounded-lg border-2 border-slate-700 bg-slate-950/60 p-3 transition-colors">
        {/* 캡 조립 모터 #1 — 평상시 Spin, 과부하 시 Shake */}
        <div className="flex flex-col items-center gap-1.5">
          <motion.div
            className="relative"
            animate={isMotorFault ? { x: [0, -4, 4, -3, 3, 0], y: [0, 2, -2, 1, -1, 0] } : { x: 0, y: 0 }}
            transition={isMotorFault ? { duration: 0.28, repeat: Infinity } : { duration: 0.2 }}
          >
            <motion.div
              className={`flex h-20 w-20 items-center justify-center rounded-full border-4 ${isMotorFault ? 'border-red-500 text-red-400' : 'border-slate-600 text-sky-300'} bg-slate-900 shadow-md`}
              animate={{ rotate: 360 }}
              transition={{ duration: spinDur, repeat: Infinity, ease: 'linear' }}
            >
              <Cog size={50} strokeWidth={1.6} />
            </motion.div>
            <span className="absolute -left-2 -top-2 flex h-6 w-6 items-center justify-center rounded-md bg-slate-800 font-mono text-[10px] text-slate-300 border border-slate-700">
              #1
            </span>
            {isMotorFault && (
              <motion.div className="absolute -right-2 -top-2 text-red-400" animate={{ opacity: [1, 0.1, 1], scale: [1, 1.2, 1] }} transition={{ duration: 0.5, repeat: Infinity }}>
                <AlertTriangle size={24} className="fill-red-500/30" />
              </motion.div>
            )}
          </motion.div>
          <div className="text-center">
            <span className="block text-xs font-bold text-slate-200">용기 캡핑 모터 #1</span>
            <span className="block text-[10px] text-slate-400">
              {isMotorFault ? '진동 이상 감지 중' : '정속 회전 중'}
            </span>
          </div>
        </div>

        {/* 계기판 */}
        <div className="flex flex-col items-center">
          <div className="flex items-center gap-1 mb-0.5">
            <span className="text-[11px] font-bold text-slate-300">SVM 합성 진동 가속도</span>
            <span className="text-[10px] text-slate-400">(임계치: 7.0)</span>
          </div>
          {/* 게이지 + 우측 화살표(+1.5) 버튼 */}
          <div className="relative flex items-center justify-center">
            <SvmGauge value={motor.svm} />
            <button
              onClick={() => stepMotorSvm(1.5)}
              className="group absolute -right-9 top-1/2 -translate-y-1/2 flex h-8 w-8 flex-col items-center justify-center rounded-lg border-2 border-red-500/70 bg-red-500/20 text-red-300 shadow-md shadow-red-500/20 transition-all hover:scale-110 hover:border-red-400 hover:bg-red-500/35 active:scale-95"
              aria-label="SVM 진동 1.5 증가"
              title="SVM 합성 진동 가속도 +1.5 m/s² 상승 (클릭 시 1.5씩 증가, 7.0 돌파 시 경보 및 안전 인터록 발동)"
            >
              <ArrowUp size={16} className="text-red-300 transition-transform group-hover:-translate-y-0.5" />
              <span className="font-mono text-[8px] font-black leading-none text-red-200">+1.5</span>
            </button>
          </div>
          <div className="mt-1 flex items-center gap-3 font-mono text-xs">
            <div className="rounded bg-slate-900 px-2 py-0.5 text-slate-300 border border-slate-800">
              <span className="text-slate-500 text-[10px] mr-1">토크:</span>
              <span className="font-bold">{motor.torque_nm.toFixed(1)} N·m</span>
            </div>
            <div className="rounded bg-slate-900 px-2 py-0.5 text-slate-300 border border-slate-800">
              <span className="text-slate-500 text-[10px] mr-1">회전수:</span>
              <span className="font-bold">{Math.round(motor.rpm)} RPM</span>
            </div>
          </div>
          <span className="mt-1 text-[9px] text-slate-400">
            정상(0~4) / 주의(4~7) / 이상 경보(7~10)
          </span>
        </div>
      </div>

      {/* ── 컨베이어 벨트 ── */}
      <motion.div
        animate={isLineVibration ? { x: [0, -2, 2, 0] } : isConveyorHalt ? { x: 0 } : { x: 0 }}
        transition={isLineVibration ? { duration: 0.25, repeat: Infinity } : { duration: 0.2 }}
        className={`relative rounded-lg border-2 p-2.5 transition-colors ${
          isConveyorHalt
            ? 'border-amber-500 bg-amber-950/40 shadow-lg shadow-amber-500/20 ring-1 ring-amber-500/40'
            : isLineVibration
              ? 'border-orange-500 bg-orange-950/40 shadow-lg shadow-orange-500/25 ring-1 ring-orange-500/50'
              : 'border-slate-700 bg-slate-950'
        }`}
      >
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-1 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-200">화장품 용기 충진·이송 컨베이어 라인</span>
            <span
              className={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 font-mono text-[10px] font-bold ${
                isConveyorHalt
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : isLineVibration
                    ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40 animate-pulse'
                    : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${isConveyorHalt ? 'bg-amber-400' : isLineVibration ? 'bg-orange-500 animate-ping' : 'bg-emerald-400'}`} />
              {isConveyorHalt ? '🛑 안전 인터록 발동 (공정 정지)' : isLineVibration ? '⚠️ 비정상 급가속 (2.8 m/s)' : '정상 정속 이송 중 (1.0 m/s)'}
            </span>
          </div>
          <span className={`font-mono text-[11px] font-bold ${isConveyorHalt ? 'text-amber-300' : isLineVibration ? 'text-orange-400' : 'text-slate-400'}`}>
            {isConveyorHalt
              ? '불량품 누출 방지 안전 인터록 대기'
              : isLineVibration
                ? '⚠️ 라인 진동 감지 · 용기 전도 위험'
                : '라인 안정 운영'}
          </span>
        </div>

        {/* 벨트 레일 */}
        <div className={`relative h-16 overflow-hidden rounded-md border ${isConveyorHalt ? 'border-amber-500/40 bg-amber-950/20' : isLineVibration ? 'border-orange-500/40 bg-orange-950/30' : 'border-slate-800 bg-slate-900/90'}`}>
          {/* 상단 사이드 가이드 레일 */}
          <div className="absolute inset-x-0 top-1 h-0.5 bg-slate-700/60" />

          {/* 벨트 본체 패턴 (바닥 밀착) */}
          <div
            className={`absolute inset-x-0 bottom-0 h-4.5 border-t border-slate-700/80 ${beltCls}`}
            style={{
              background: isConveyorHalt
                ? 'repeating-linear-gradient(90deg, #78350f 0 12px, #451a03 12px 24px)'
                : isLineVibration
                  ? 'repeating-linear-gradient(45deg, #f97316 0 14px, #431407 14px 28px)'
                  : 'repeating-linear-gradient(90deg, #334155 0 12px, #1e293b 12px 24px)',
            }}
          />

          {/* 이송 중인 화장품 용기들 (캐리어 퍽에 안착되어 벨트와 동기화 이동) */}
          {[0, 1, 2, 3, 4].map((i) => {
            const tiltAngles = [-10, 12, -8, 14, -10]
            const tilt = tiltAngles[i % tiltAngles.length]
            const staticLeft = `${18 + i * 18}%`
            return (
              <motion.div
                key={`${i}-${isConveyorHalt ? 'halt' : bottleDur}`}
                className="absolute bottom-1 select-none"
                initial={isConveyorHalt ? { left: staticLeft } : { left: '-10%' }}
                animate={isConveyorHalt ? { left: staticLeft } : { left: '104%' }}
                transition={isConveyorHalt ? { duration: 0.1 } : { duration: bottleDur, repeat: Infinity, ease: 'linear', delay: (i * bottleDur) / 5 }}
              >
                <motion.div
                  animate={
                    isLineVibration
                      ? {
                          rotate: [0, tilt, 0],
                          y: [0, -4, 0],
                        }
                      : isConveyorHalt
                        ? { rotate: 0, y: 0 }
                        : { rotate: 0, y: 0 }
                  }
                  transition={
                    isLineVibration
                      ? { duration: 0.35, repeat: Infinity, ease: 'easeInOut', delay: i * 0.08 }
                      : { duration: 0.2 }
                  }
                  className="relative flex flex-col items-center"
                >
                  {/* 화장품 용기 본체 */}
                  <span className={`text-2xl leading-none ${isLineVibration ? 'drop-shadow-[0_0_6px_rgba(249,115,22,0.8)]' : isConveyorHalt ? 'opacity-70' : 'drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]'}`}>
                    🧴
                  </span>

                  {/* 벨트 위 고정용 캐리어 퍽 (Puck Tray) - 벨트 위에 실려있는 물리적 받침대 */}
                  <div
                    className={`-mt-0.5 flex h-2 w-7 items-center justify-center rounded-sm border shadow-sm transition-colors ${
                      isLineVibration ? 'border-orange-500 bg-orange-950' : isConveyorHalt ? 'border-amber-500 bg-amber-950/80' : 'border-slate-500 bg-slate-800'
                    }`}
                  >
                    <div className={`h-1 w-5 rounded-full ${isLineVibration ? 'bg-orange-500/70' : isConveyorHalt ? 'bg-amber-400/50' : 'bg-slate-600'}`} />
                  </div>

                  {/* 벨트 표면 접지 그림자 */}
                  <div className="h-0.5 w-6 rounded-full bg-black/60 blur-[1px]" />
                </motion.div>
              </motion.div>
            )
          })}
        </div>

        {/* 컨베이어 하단 실시간 상태 정보 */}
        <div className="mt-1.5 flex flex-wrap items-center justify-between gap-1 border-t border-slate-800/80 pt-1 font-mono text-[10px] text-slate-400">
          <span>
            이송 속도:{' '}
            <b className={isLineVibration ? 'text-orange-400 font-bold' : isConveyorHalt ? 'text-amber-400 font-bold' : 'text-slate-200'}>
              {isLineVibration ? '2.8 m/s (과속 경보)' : isConveyorHalt ? '0.0 m/s (인터록 정지)' : '1.0 m/s (표준)'}
            </b>
          </span>
          <span>
            라인 상태:{' '}
            <b className={isLineVibration ? 'text-orange-400 font-bold' : isConveyorHalt ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
              {isLineVibration ? 'VIBRATING (진동 경보)' : isConveyorHalt ? 'INTERLOCK HALT (안전 정지)' : 'STABLE (안정 운영)'}
            </b>
          </span>
        </div>
      </motion.div>

      {/* ── GKE Worker Container Rack ── */}
      <div className="rounded-lg border-2 border-slate-700 bg-slate-950/60 p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-1 text-slate-300">
          <div className="flex items-center gap-1.5">
            <Container size={16} className="text-sky-400" />
            <span className="text-xs font-bold text-slate-200">GKE 스트림 처리 컨테이너 파드 랙</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">
              파드 가동 현황:
            </span>
            <span className="font-mono text-xs font-bold text-sky-300">
              {activeCount} 활성 {startingCount > 0 && `(+${startingCount} 기동)`} {terminatingCount > 0 && `(-${terminatingCount} 종료)`} / 총 {pods.length}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {pods.map((p) => (
            <Pod key={p.id} pod={p} />
          ))}
        </div>

        <div className="mt-2.5 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[10px] text-slate-400">
          <span>※ 큐 적체 발생 시 자동 확장(Scale-up)되며, 적체 해소 후 안전하게 순차 회수(Scale-in)합니다.</span>
          <div className="flex items-center gap-2 font-mono">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-400" />활성</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-sky-400" />기동 중</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-400" />종료 중</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-slate-600" />대기</span>
          </div>
        </div>
      </div>
    </section>
  )
}
