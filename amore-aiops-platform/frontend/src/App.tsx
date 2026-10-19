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
      <header className="panel flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <Factory className="text-sky-400" size={26} />
          <h1 className="text-lg font-extrabold tracking-wide">DIGITAL TWIN &amp; AIOPS CENTER</h1>
          <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-400' : 'animate-blink bg-red-500'}`} />
          {snap && <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-[11px] uppercase text-slate-400">{snap.mode}</span>}
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
