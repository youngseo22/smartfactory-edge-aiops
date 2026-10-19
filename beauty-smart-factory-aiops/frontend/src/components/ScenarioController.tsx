import React from "react";
import { CheckCircle2, Flame, Snowflake, Loader2 } from "lucide-react";
import type { ScenarioId } from "../types";

interface Props {
  currentScenario: ScenarioId;
  onTrigger: (id: ScenarioId) => void;
  pending: ScenarioId | null;
}

export const ScenarioController: React.FC<Props> = ({
  currentScenario,
  onTrigger,
  pending,
}) => {
  return (
    <div className="flex items-center gap-2">
      {/* Normal Mode Button */}
      <button
        onClick={() => onTrigger("NORMAL")}
        disabled={pending !== null}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 ${
          currentScenario === "NORMAL"
            ? "border-emerald-500 bg-emerald-950/60 text-neon-lime shadow-glow-lime"
            : "border-white/10 bg-ink-900/60 text-slate-400 hover:border-white/20 hover:text-slate-200"
        }`}
      >
        {pending === "NORMAL" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <CheckCircle2 className="h-3.5 w-3.5" />
        )}
        <span>Normal</span>
      </button>

      {/* Scenario 1 Button */}
      <button
        onClick={() => onTrigger("SCENARIO_1")}
        disabled={pending !== null}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 ${
          currentScenario === "SCENARIO_1"
            ? "border-rose-500 bg-rose-950/60 text-neon-coral shadow-glow-red animate-pulse"
            : "border-white/10 bg-ink-900/60 text-slate-400 hover:border-rose-500/40 hover:text-rose-300"
        }`}
      >
        {pending === "SCENARIO_1" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Flame className="h-3.5 w-3.5 text-neon-coral" />
        )}
        <span>Scenario 1 (Motor & Surge)</span>
      </button>

      {/* Scenario 2 Button */}
      <button
        onClick={() => onTrigger("SCENARIO_2")}
        disabled={pending !== null}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 ${
          currentScenario === "SCENARIO_2"
            ? "border-cyan-500 bg-cyan-950/60 text-neon-cyan shadow-glow animate-pulse"
            : "border-white/10 bg-ink-900/60 text-slate-400 hover:border-cyan-500/40 hover:text-cyan-300"
        }`}
      >
        {pending === "SCENARIO_2" ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Snowflake className="h-3.5 w-3.5 text-neon-cyan" />
        )}
        <span>Scenario 2 (ColdChain Failover)</span>
      </button>
    </div>
  );
};
