import React from "react";
import { MessageSquare, Wrench, Layers, ShieldCheck, ArrowRight, Zap, RefreshCw } from "lucide-react";
import type { SlackCard, ScaleUpWidget, FailoverWidget } from "../types";

interface Props {
  remediation?: {
    slack: SlackCard;
    scale_up: ScaleUpWidget;
    failover: FailoverWidget;
  };
}

export const RemediationVisualDock: React.FC<Props> = ({ remediation }) => {
  const slack = remediation?.slack;
  const scaleUp = remediation?.scale_up;
  const failover = remediation?.failover;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Widget 1: Slack RAG Mini Card */}
      <div
        className={`panel p-3.5 flex flex-col justify-between border transition-all duration-300 ${
          slack?.active
            ? "border-rose-500/50 bg-rose-950/20 shadow-glow-red"
            : "border-white/10 opacity-70"
        }`}
      >
        <div className="flex items-center justify-between border-b border-white/5 pb-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
            <MessageSquare className="h-4 w-4 text-neon-coral" />
            <span>SLACK RAG REMEDIATION</span>
          </div>
          {slack?.active && (
            <span className="chip border-rose-500/50 bg-rose-950/60 text-neon-coral animate-pulse">
              POPUP FIRED
            </span>
          )}
        </div>

        {slack?.active ? (
          <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-700/80 my-2 shadow-md">
            <div className="flex items-center justify-between mb-2">
              <span className="chip border-cyan-500/40 bg-cyan-950/40 text-neon-cyan">
                📖 {slack.page ?? "Manual p.42"}
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {(slack.confidence * 100).toFixed(0)}% Match
              </span>
            </div>
            <div className="flex items-center gap-2 text-neon-amber font-mono font-bold text-sm">
              <Wrench className="h-4 w-4" />
              <span>{slack.keyword ?? "Torque -0.5 Turn"}</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {slack.metric ?? "SVM 8.5 DETECTED"}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-5 text-slate-500 text-xs">
            <span>RAG Engine Standby</span>
          </div>
        )}

        <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
          <span>Target: Cap Assembly #1</span>
          <span>Action: Auto Alert</span>
        </div>
      </div>

      {/* Widget 2: Auto Scale-Up Meter */}
      <div
        className={`panel p-3.5 flex flex-col justify-between border transition-all duration-300 ${
          scaleUp?.active
            ? "border-neon-teal/50 bg-teal-950/20 shadow-glow"
            : "border-white/10 opacity-70"
        }`}
      >
        <div className="flex items-center justify-between border-b border-white/5 pb-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
            <Layers className="h-4 w-4 text-neon-teal" />
            <span>AUTO SCALE-UP METER</span>
          </div>
          {scaleUp?.active && (
            <span className="chip border-teal-500/50 bg-teal-950/60 text-neon-teal animate-pulse">
              300% BOOST
            </span>
          )}
        </div>

        <div className="flex flex-col items-center justify-center my-2 gap-2">
          {/* Pods Visual Blocks: [■][■][□][□][□][□] -> [■][■][■][■][■][■] */}
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5, 6].map((i) => {
              const isFilled = i <= (scaleUp?.active_pods ?? 2);
              const isExtra = i > 2;
              return (
                <div
                  key={i}
                  className={`h-5 w-5 rounded flex items-center justify-center text-[9px] font-mono font-bold border transition-all duration-300 ${
                    isFilled
                      ? isExtra
                        ? "bg-neon-teal text-slate-950 border-neon-teal shadow-glow"
                        : "bg-cyan-500 text-slate-950 border-cyan-500"
                      : "bg-slate-900 border-slate-700 text-slate-600"
                  }`}
                >
                  {isFilled && isExtra ? <Zap className="h-3 w-3" /> : i}
                </div>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-200 mt-1">
            <span>2 Pods</span>
            <ArrowRight className="h-3.5 w-3.5 text-neon-teal" />
            <span className="text-neon-teal">{scaleUp?.active_pods ?? 2} Pods (Max 6)</span>
          </div>
        </div>

        <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
          <span>Throughput: {scaleUp?.throughput_pct ?? 100}% ▲</span>
          <span>Target: Dataflow Workers</span>
        </div>
      </div>

      {/* Widget 3: Traffic Failover Switchboard */}
      <div
        className={`panel p-3.5 flex flex-col justify-between border transition-all duration-300 ${
          failover?.active
            ? "border-neon-violet/50 bg-violet-950/20 shadow-glow"
            : "border-white/10 opacity-70"
        }`}
      >
        <div className="flex items-center justify-between border-b border-white/5 pb-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
            <RefreshCw className="h-4 w-4 text-neon-violet" />
            <span>TRAFFIC FAILOVER SWITCH</span>
          </div>
          <span className="chip border-emerald-500/40 bg-emerald-950/40 text-neon-lime">
            <ShieldCheck className="h-3 w-3" />
            <span>0% LOSS</span>
          </span>
        </div>

        <div className="flex items-center justify-around my-2 px-2">
          {/* Zone A Indicator */}
          <div className="flex flex-col items-center">
            <span className="text-[11px] font-mono text-slate-400">Zone A</span>
            <span className="text-sm font-bold text-slate-300 mt-1">
              {failover?.active ? "❌ OFFLINE" : "🟢 ACTIVE"}
            </span>
          </div>

          {/* Reroute Switch Arrow */}
          <div className="flex flex-col items-center">
            <ArrowRight
              className={`h-5 w-5 ${
                failover?.active ? "text-neon-violet animate-bounce" : "text-slate-600"
              }`}
            />
            <span className="text-[9px] font-mono text-neon-violet">
              {failover?.active ? "REROUTED" : "NORMAL"}
            </span>
          </div>

          {/* Zone B Indicator */}
          <div className="flex flex-col items-center">
            <span className="text-[11px] font-mono text-slate-400">Zone B</span>
            <span
              className={`text-sm font-bold mt-1 ${
                failover?.active ? "text-neon-lime" : "text-slate-500"
              }`}
            >
              {failover?.active ? "🟢 BACKUP ON" : "⚫ STANDBY"}
            </span>
          </div>
        </div>

        <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
          <span>Heartbeat: {failover?.active ? "Timed out (3s)" : "Normal"}</span>
          <span>Status: Protected</span>
        </div>
      </div>
    </div>
  );
};
