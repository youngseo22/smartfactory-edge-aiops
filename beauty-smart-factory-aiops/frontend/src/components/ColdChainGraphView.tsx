import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Thermometer, ShieldCheck, WifiOff, CheckCircle2 } from "lucide-react";
import type { ColdChainState, RoutingState } from "../types";

interface Props {
  coldchain?: ColdChainState;
  routing?: RoutingState;
}

export const ColdChainGraphView: React.FC<Props> = ({ coldchain, routing }) => {
  const data = coldchain?.temp_history ?? [];
  const zones = coldchain?.zones ?? {};
  const zoneA = zones["ZONE_A"];
  const zoneB = zones["ZONE_B"];
  const isFailover = routing?.failover_active ?? false;
  const dataLossPct = routing?.data_loss_pct ?? 0;

  // 차트 툴팁 커스텀
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-2 rounded shadow-lg text-[10px] font-mono">
          <div className="text-slate-400">Time: {new Date(p.t * 1000).toLocaleTimeString()}</div>
          {p.a_primary !== null && (
            <div className="text-neon-cyan">Zone A (Primary): {p.a_primary?.toFixed(1)}℃</div>
          )}
          {p.a_backup !== null && (
            <div className="text-neon-violet font-bold">Zone A (Via Zone B): {p.a_backup?.toFixed(1)}℃</div>
          )}
          {p.zone_b !== null && (
            <div className="text-neon-teal">Zone B: {p.zone_b?.toFixed(1)}℃</div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="panel p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-2">
        <div className="panel-title">
          <Thermometer className="h-4 w-4 text-neon-cyan" />
          <span>Cold-Chain Live Temperature & Node Map</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="chip border-emerald-500/30 bg-emerald-950/40 text-neon-lime">
            <ShieldCheck className="h-3 w-3" />
            <span>Loss {dataLossPct}%</span>
          </span>
          {isFailover && (
            <span className="chip border-violet-500/50 bg-violet-950/50 text-neon-violet animate-pulse">
              FAILOVER ACTIVE
            </span>
          )}
        </div>
      </div>

      {/* Real-time Recharts Line Chart */}
      <div className="h-44 w-full relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="primaryGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="backupGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="t" tick={false} stroke="#475569" />
            <YAxis domain={[0, 15]} ticks={[0, 4, 8, 12]} stroke="#475569" />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Threshold Line at 8.0℃ */}
            <ReferenceLine
              y={8.0}
              stroke="#fb7185"
              strokeDasharray="4 4"
              label={{ value: "Threshold (8.0℃)", fill: "#fb7185", fontSize: 10, position: "insideTopRight" }}
            />

            {/* Zone A Primary Line */}
            <Area
              type="monotone"
              dataKey="a_primary"
              stroke="#22d3ee"
              strokeWidth={2}
              fill="url(#primaryGrad)"
              isAnimationActive={false}
            />

            {/* Zone A Failover Line (Continuous via Zone B) */}
            <Area
              type="monotone"
              dataKey="a_backup"
              stroke="#a78bfa"
              strokeWidth={2.5}
              fill="url(#backupGrad)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Warehouse Node Map (Zone A -> Zone B Failover) */}
      <div className="grid grid-cols-2 gap-4 relative pt-2">
        {/* Dynamic SVG Rerouting line */}
        {isFailover && (
          <div className="absolute inset-x-12 top-1/2 -translate-y-1/2 flex items-center justify-center pointer-events-none z-10">
            <svg className="w-full h-8 overflow-visible">
              <line
                x1="20%"
                y1="50%"
                x2="80%"
                y2="50%"
                stroke="#a78bfa"
                strokeWidth="3"
                strokeDasharray="6 4"
                className="animate-dash"
              />
            </svg>
          </div>
        )}

        {/* Zone A Box */}
        <div
          className={`p-3 rounded-xl border flex flex-col gap-2 transition-all duration-300 ${
            zoneA?.status === "OFFLINE"
              ? "border-rose-500/50 bg-rose-950/20 shadow-glow-red"
              : "border-cyan-500/30 bg-ink-850"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-xs text-slate-200">
              <span>❄️ Zone A</span>
              <span className="text-[10px] text-slate-400">(Primary)</span>
            </div>
            {zoneA?.status === "OFFLINE" ? (
              <span className="flex items-center gap-1 text-[10px] font-bold text-neon-coral animate-pulse">
                <WifiOff className="h-3 w-3" />
                <span>DOWN</span>
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-neon-lime">
                <CheckCircle2 className="h-3 w-3" />
                <span>LIVE</span>
              </span>
            )}
          </div>
          <div className="flex items-baseline justify-between text-slate-300 font-mono">
            <span className="text-xl font-bold">
              {zoneA?.temperature_c?.toFixed(1) ?? "--"}
              <span className="text-xs font-normal text-slate-400">℃</span>
            </span>
            <span className="text-xs text-slate-400">
              {zoneA?.humidity_pct?.toFixed(0) ?? "--"}% RH
            </span>
          </div>
        </div>

        {/* Zone B Box */}
        <div
          className={`p-3 rounded-xl border flex flex-col gap-2 transition-all duration-300 ${
            isFailover
              ? "border-neon-violet bg-violet-950/30 shadow-glow"
              : "border-slate-700 bg-ink-850"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-xs text-slate-200">
              <span>❄️ Zone B</span>
              <span className="text-[10px] text-slate-400">(Backup)</span>
            </div>
            {isFailover ? (
              <span className="chip border-violet-500/50 bg-violet-950/60 text-neon-violet font-bold animate-pulse">
                BACKUP ACTIVE
              </span>
            ) : (
              <span className="text-[10px] text-slate-400">Standby</span>
            )}
          </div>
          <div className="flex items-baseline justify-between text-slate-300 font-mono">
            <span className="text-xl font-bold">
              {zoneB?.temperature_c?.toFixed(1) ?? "--"}
              <span className="text-xs font-normal text-slate-400">℃</span>
            </span>
            <span className="text-xs text-slate-400">
              {zoneB?.humidity_pct?.toFixed(0) ?? "--"}% RH
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
