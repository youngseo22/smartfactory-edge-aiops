import { Factory, Loader2 } from 'lucide-react'
import ColdChainGraphView from './components/ColdChainGraphView'
import FactoryContainerView from './components/FactoryContainerView'
import PipelineTopology from './components/PipelineTopology'
import RemediationVisualDock from './components/RemediationVisualDock'
import ScenarioController from './components/ScenarioController'
import { useDashboard } from './hooks/useDashboard'

export default function App() {
  const { snap, connected } = useDashboard()

  return (
    <div className="mx-auto flex min-h-screen max-w-[1400px] flex-col gap-4 p-4">
      {/* 헤더 + 시나리오 컨트롤러 */}
      <header className="panel flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30">
            <Factory className="text-sky-400" size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-wide text-white">
                AMOREPACIFIC AIOps &amp; DIGITAL TWIN
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
        <ScenarioController active={snap?.active_scenarios ?? []} />
      </header>

      {!snap ? (
        <div className="flex flex-1 items-center justify-center text-sky-400">
          <Loader2 size={44} className="animate-spin" />
        </div>
      ) : (
        <>
          <PipelineTopology snap={snap} />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <FactoryContainerView snap={snap} />
            <ColdChainGraphView snap={snap} />
          </div>
          <RemediationVisualDock snap={snap} />
        </>
      )}
    </div>
  )
}
