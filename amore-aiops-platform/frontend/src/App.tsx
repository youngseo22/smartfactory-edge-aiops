import { Factory, Loader2 } from 'lucide-react'
import ColdChainGraphView from './components/ColdChainGraphView'
import PipelineTopology from './components/PipelineTopology'
import ProcessingContainerView from './components/ProcessingContainerView'
import RemediationVisualDock from './components/RemediationVisualDock'
import ScenarioController from './components/ScenarioController'
import SmartManufacturingView from './components/SmartManufacturingView'
import { useDashboard } from './hooks/useDashboard'

export default function App() {
  const { snap, connected } = useDashboard()

  return (
    <div className="mx-auto flex min-h-screen max-w-[1520px] flex-col gap-4 p-4">
      {/* 헤더 + 시나리오 컨트롤러 */}
      <header className="panel flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30">
            <Factory className="text-sky-400" size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-wide text-white">
                SMART FACTORY AIOps PLATFORM
              </h1>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                connected ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-red-500/15 text-red-300 border border-red-500/30'
              }`}>
                <span className={`h-2 w-2 rounded-full ${connected ? 'bg-emerald-400' : 'animate-blink bg-red-500'}`} />
                {connected ? '실시간 연동 LIVE' : '연결 끊김 DISCONNECTED'}
              </span>
            </div>
          </div>
        </div>
        <ScenarioController active={snap?.active_scenarios ?? []} snap={snap} />
      </header>

      {!snap ? (
        <div className="flex flex-1 items-center justify-center text-sky-400">
          <Loader2 size={44} className="animate-spin" />
        </div>
      ) : (
        <>
          {/* 상위: SECTION 1 실시간 데이터 파이프라인 & Pub/Sub 큐 토폴로지 */}
          <PipelineTopology snap={snap} />

          {/* 중위: SECTION 2 스마트 제조 라인, SECTION 3 스마트 콜드체인 실시간 온도, SECTION 4 처리 컨테이너 */}
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <SmartManufacturingView snap={snap} />
            <ColdChainGraphView snap={snap} />
            <ProcessingContainerView snap={snap} />
          </div>

          {/* 하위: SECTION 5 AIOps 실시간 자율 치유 및 조치 현황 */}
          <RemediationVisualDock snap={snap} />
        </>
      )}
    </div>
  )
}
