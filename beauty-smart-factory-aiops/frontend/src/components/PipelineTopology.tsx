import React from "react";
import { motion } from "framer-motion";
import { Cpu, Radio, Database, Layers, ArrowRight } from "lucide-react";
import type { PipelineStats } from "../types";

interface Props {
  stats?: PipelineStats;
}

export const PipelineTopology: React.FC<Props> = ({ stats }) => {
  const edgeRate = stats?.edge_rate ?? 0;
  const ingressRate = stats?.ingress_rate ?? 0;
  const backlog = stats?.backlog_count ?? 0;
  const backlogThreshold = stats?.backlog_threshold ?? 1000;
  const bottleneckPct = stats?.bottleneck_pct ?? 0;
  const bqRows = stats?.bq_rows ?? 0;
  const aiEvents = stats?.ai_events ?? 0;

  // 1000건 초과 시 주황/적색 경고
  const isHighBacklog = backlog >= backlogThreshold;
  const cylinderColor = isHighBacklog
    ? "from-amber-500 to-rose-600 shadow-glow-red"
    : "from-cyan-500 to-teal-400 shadow-glow";

  return (
    <div className="panel p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <div className="panel-title">
          <Layers className="h-4 w-4 text-neon-cyan" />
          <span>Live Streaming Pipeline Topology</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="chip border-cyan-500/30 bg-cyan-950/40 text-neon-cyan">
            <Radio className="h-3 w-3 animate-pulse" />
            <span>{ingressRate.toFixed(0)} msg/s</span>
          </span>
          <span className="chip border-slate-700 bg-slate-900 text-slate-400">
            <Database className="h-3 w-3" />
            <span>BQ {bqRows.toLocaleString()}</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-center relative">
        {/* Node 1: Edge Layer */}
        <div className="flex flex-col items-center justify-center p-3 rounded-xl border border-white/10 bg-ink-850/80 shadow-md">
          <div className="h-10 w-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-neon-cyan mb-1.5">
            <Cpu className="h-5 w-5" />
          </div>
          <div className="text-xs font-bold text-slate-200">Edge IoT Nodes</div>
          <div className="text-[10px] text-slate-400 num">{edgeRate.toFixed(0)} evt/s</div>
        </div>

        {/* Animated Pipe 1 */}
        <div className="hidden md:flex items-center justify-center relative overflow-hidden h-6">
          <div className="w-full h-1 bg-slate-800 rounded-full relative">
            <motion.div
              className="absolute top-0 bottom-0 w-8 bg-gradient-to-r from-transparent via-neon-cyan to-transparent rounded-full shadow-glow"
              animate={{ x: ["-100%", "200%"] }}
              transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
            />
          </div>
          <ArrowRight className="h-3.5 w-3.5 text-slate-600 absolute right-0" />
        </div>

        {/* Node 2: Ingestion Gateway */}
        <div className="flex flex-col items-center justify-center p-3 rounded-xl border border-white/10 bg-ink-850/80 shadow-md">
          <div className="h-10 w-10 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-neon-teal mb-1.5">
            <Radio className="h-5 w-5" />
          </div>
          <div className="text-xs font-bold text-slate-200">Gateway WS</div>
          <div className="text-[10px] text-neon-teal num">{ingressRate.toFixed(0)} rx/s</div>
        </div>

        {/* Animated Pipe 2 */}
        <div className="hidden md:flex items-center justify-center relative overflow-hidden h-6">
          <div className="w-full h-1 bg-slate-800 rounded-full relative">
            <motion.div
              className="absolute top-0 bottom-0 w-8 bg-gradient-to-r from-transparent via-neon-teal to-transparent rounded-full"
              animate={{ x: ["-100%", "200%"] }}
              transition={{ repeat: Infinity, duration: 1.0, ease: "linear" }}
            />
          </div>
          <ArrowRight className="h-3.5 w-3.5 text-slate-600 absolute right-0" />
        </div>

        {/* Node 3 & Cylinder: Pub/Sub Load Leveling Tank */}
        <div className={`flex flex-col p-3 rounded-xl border ${isHighBacklog ? 'border-rose-500/50 bg-rose-950/20' : 'border-white/10 bg-ink-850/80'} shadow-md relative`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <span>🛢️ Pub/Sub Buffer</span>
            </span>
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${isHighBacklog ? 'bg-rose-500/20 text-rose-300 font-bold animate-pulse' : 'bg-slate-800 text-slate-300'}`}>
              {bottleneckPct}%
            </span>
          </div>

          {/* Liquid Cylinder Gauge */}
          <div className="w-full bg-slate-900 rounded-lg h-5 border border-slate-700 overflow-hidden relative p-0.5">
            <motion.div
              className={`h-full rounded-md bg-gradient-to-r ${cylinderColor}`}
              initial={false}
              animate={{ width: `${Math.min(100, (backlog / 1500) * 100)}%` }}
              transition={{ type: "spring", stiffness: 120, damping: 20 }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-[10px] font-mono font-bold text-white drop-shadow">
              {backlog} / {backlogThreshold}
            </div>
          </div>

          <div className="flex justify-between items-center mt-2 text-[9px] text-slate-400">
            <span>Route A (DW): {stats?.route_a_rate?.toFixed(0) ?? 0}</span>
            <span className="text-neon-coral">Route B: {aiEvents}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
