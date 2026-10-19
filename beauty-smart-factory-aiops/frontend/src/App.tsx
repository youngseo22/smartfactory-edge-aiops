import React from "react";
import { useDashboard } from "./useDashboard";
import { ScenarioController } from "./components/ScenarioController";
import { PipelineTopology } from "./components/PipelineTopology";
import { FactoryContainerView } from "./components/FactoryContainerView";
import { ColdChainGraphView } from "./components/ColdChainGraphView";
import { RemediationVisualDock } from "./components/RemediationVisualDock";
import { Factory, Radio, Shield, Sparkles } from "lucide-react";

export const App: React.FC = () => {
  const { snap, conn, trigger, pending } = useDashboard();

  const isConnected = conn === "open";
  const scenario = snap?.scenario ?? "NORMAL";
  const mode = snap?.mode ?? "MOCK";

  return (
    <div className="min-h-screen text-slate-100 p-4 md:p-6 max-w-7xl mx-auto flex flex-col gap-5">
      {/* Top Header Bar */}
      <header className="panel p-4 flex flex-col md:flex-row items-center justify-between gap-4 border-white/10 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-500 to-teal-400 flex items-center justify-center text-slate-950 shadow-glow">
            <Factory className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base md:text-lg font-bold tracking-tight text-white flex items-center gap-2">
                <span>DIGITAL TWIN & AIOPS CENTER</span>
              </h1>
              <span className="chip border-cyan-500/40 bg-cyan-950/40 text-neon-cyan">
                {mode}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Smart Factory & Fulfillment Autonomous Remediation
            </p>
          </div>
        </div>

        {/* Header Right: Connection & Scenario Controller */}
        <div className="flex items-center gap-4 flex-wrap justify-end">
          <div className="flex items-center gap-1.5 text-[11px] font-mono">
            {isConnected ? (
              <span className="flex items-center gap-1.5 text-neon-lime">
                <span className="led led-green" />
                <span>WS LIVE</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-neon-coral animate-pulse">
                <span className="led led-red" />
                <span>CONNECTING</span>
              </span>
            )}
          </div>

          <ScenarioController
            currentScenario={scenario}
            onTrigger={trigger}
            pending={pending}
          />
        </div>
      </header>

      {/* Layer 1: Live Pipeline Flow & Pub/Sub Buffer */}
      <section>
        <PipelineTopology stats={snap?.pipeline} />
      </section>

      {/* Layer 2: Twin Columns (Factory Equipment Bay + ColdChain Node Map) */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <FactoryContainerView factory={snap?.factory} />
        <ColdChainGraphView
          coldchain={snap?.coldchain}
          routing={snap?.routing}
        />
      </section>

      {/* Layer 3: Visual AI Remediation Dock */}
      <section className="flex flex-col gap-2">
        <div className="panel-title px-1">
          <Sparkles className="h-3.5 w-3.5 text-neon-amber" />
          <span>Autonomous AI Remediation Dock</span>
        </div>
        <RemediationVisualDock remediation={snap?.remediation} />
      </section>

      {/* Footer Info Bar */}
      <footer className="flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 font-mono border-t border-white/5 pt-3">
        <div className="flex items-center gap-3">
          <span>AIOps Enterprise Platform v1.0</span>
          <span>•</span>
          <span className="flex items-center gap-1 text-slate-400">
            <Radio className="h-3 w-3 text-neon-cyan" />
            <span>0.5s Sliding Telemetry</span>
          </span>
        </div>
        <div className="flex items-center gap-2 mt-2 sm:mt-0">
          <Shield className="h-3.5 w-3.5 text-neon-lime" />
          <span>Vertex AI RAG Guided Autonomous Failover & Scale-Up</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
