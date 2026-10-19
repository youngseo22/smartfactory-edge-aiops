import React from "react";
import { motion } from "framer-motion";
import { Cog, Zap, AlertTriangle, CheckCircle } from "lucide-react";
import type { FactoryState } from "../types";

interface Props {
  factory?: FactoryState;
}

export const FactoryContainerView: React.FC<Props> = ({ factory }) => {
  const motor = factory?.motor;
  const pods = factory?.worker_pods ?? [];
  const svm = motor?.vibration_svm ?? 2.4;
  const torque = motor?.torque_nm ?? 3.6;
  const rpm = motor?.rpm ?? 1200;
  const isVibrating = svm >= (motor?.threshold ?? 7.0);
  const isCritical = svm >= (motor?.critical ?? 10.0);
  const beltCls = isVibrating ? "animate-belt-fast" : "animate-belt";
  const bottleDur = isVibrating ? 3 : 6;

  return (
    <div className="panel-industrial p-4 flex flex-col gap-4">
      {/* Rivets */}
      <span className="rivet top-2 left-2" />
      <span className="rivet top-2 right-2" />
      <span className="rivet bottom-2 left-2" />
      <span className="rivet bottom-2 right-2" />

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-700/80 pb-2">
        <div className="panel-title text-slate-300">
          <Cog className="h-4 w-4 text-neon-amber" />
          <span>Bay #01 · Cosmetic Cap Assembly Bay</span>
        </div>
        <div className="flex items-center gap-2">
          {isVibrating ? (
            <span
              className={`chip ${
                isCritical
                  ? "border-rose-600 bg-rose-950/80 text-rose-300 font-extrabold animate-bounce"
                  : "border-rose-500/50 bg-rose-950/60 text-neon-coral animate-pulse"
              }`}
            >
              <AlertTriangle className="h-3 w-3" />
              <span>{isCritical ? "CRITICAL" : "HIGH"} SVM {svm.toFixed(1)}</span>
            </span>
          ) : (
            <span className="chip border-emerald-500/30 bg-emerald-950/40 text-neon-lime">
              <CheckCircle className="h-3 w-3" />
              <span>NORMAL</span>
            </span>
          )}
        </div>
      </div>

      {/* Upper: Motor & Conveyor Track */}
      <div className="bg-slate-950/70 rounded-xl p-3 border border-slate-800 flex flex-col gap-3 relative overflow-hidden">
        {/* Motor Status Graphic */}
        <div className="flex items-center justify-around gap-4">
          {/* Motor Spin / Shake Visual */}
          <div className="flex flex-col items-center">
            <div
              className={`relative h-20 w-20 rounded-2xl flex items-center justify-center border-2 transition-all ${
                isVibrating
                  ? "border-rose-500 bg-rose-950/50 shadow-glow-red animate-shake"
                  : "border-cyan-500/40 bg-slate-900 shadow-glow"
              }`}
            >
              <Cog
                className={`h-12 w-12 ${
                  isVibrating
                    ? "text-neon-coral animate-spin-fast"
                    : "text-neon-cyan animate-spin-slow"
                }`}
              />
              {isVibrating && (
                <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-4 w-4 bg-rose-500 text-[9px] items-center justify-center font-bold text-white">!</span>
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono mt-1 text-slate-300 font-bold">
              {motor?.sensor_id ?? "MOTOR_LINE_A_01"}
            </div>
          </div>

          {/* SVM & Torque Gauges */}
          <div className="flex-1 max-w-[200px] flex flex-col gap-2">
            <div>
              <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-0.5">
                <span>Vibration (SVM)</span>
                <span className={isVibrating ? "text-neon-coral font-bold" : "text-neon-cyan"}>
                  {svm.toFixed(2)} / 7.0
                </span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 border border-slate-700 overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    isVibrating ? "bg-rose-500 shadow-glow-red" : "bg-cyan-400"
                  }`}
                  style={{ width: `${Math.min(100, (svm / 12) * 100)}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-0.5">
                <span>Torque (Nm)</span>
                <span className="text-neon-amber font-mono">{torque.toFixed(2)} Nm</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2 border border-slate-700 overflow-hidden">
                <div
                  className="h-full bg-amber-400 transition-all duration-300"
                  style={{ width: `${Math.min(100, (torque / 6) * 100)}%` }}
                />
              </div>
            </div>

            <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
              <span>Speed:</span>
              <span className="text-slate-200 font-bold">{rpm} RPM</span>
            </div>
          </div>
        </div>

        {/* ── 컨베이어 벨트 ── */}
        <div className="relative h-14 overflow-hidden rounded-lg border-2 border-slate-700 bg-slate-950">
          <div
            className={`absolute inset-x-0 bottom-0 h-4 ${beltCls}`}
            style={{ background: "repeating-linear-gradient(90deg,#334155 0 12px,#1e293b 12px 24px)" }}
          />
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span
              key={`${i}-${bottleDur}`}
              className="absolute bottom-3 text-2xl select-none"
              initial={{ left: "-8%" }}
              animate={{ left: "104%" }}
              transition={{ duration: bottleDur, repeat: Infinity, ease: "linear", delay: (i * bottleDur) / 5 }}
            >
              🧴
            </motion.span>
          ))}
        </div>
      </div>

      {/* Lower: GKE Worker Container Rack (6 Pod Slots) */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-400">
          <span className="flex items-center gap-1.5">
            <Zap className="h-3.5 w-3.5 text-neon-cyan" />
            <span>GKE Worker Pods ({factory?.active_workers ?? 2} / 6 Active)</span>
          </span>
          <span className="chip border-slate-700 bg-slate-900 text-neon-teal">
            {factory?.throughput_pct ?? 100}% Throughput
          </span>
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
          {pods.map((pod) => {
            const isActive = pod.state === "ACTIVE";
            const isBooting = pod.state === "BOOTING";
            const isBoosted = pod.boosted;

            return (
              <div
                key={pod.pod_id}
                className={`relative flex flex-col items-center justify-center p-2 rounded-xl border text-center transition-all duration-300 ${
                  isActive
                    ? isBoosted
                      ? "border-neon-teal bg-teal-950/40 shadow-glow"
                      : "border-emerald-500/40 bg-slate-900/90"
                    : isBooting
                    ? "border-amber-400 bg-amber-950/40 animate-pulse"
                    : "border-slate-800 bg-slate-950/60 opacity-40"
                }`}
              >
                <div className="text-xs mb-1">
                  {isActive ? (
                    isBoosted ? (
                      <Zap className="h-4 w-4 text-neon-teal animate-bounce" />
                    ) : (
                      <span className="led led-green" />
                    )
                  ) : isBooting ? (
                    <span className="led led-amber" />
                  ) : (
                    <span className="led led-off" />
                  )}
                </div>
                <div className="text-[10px] font-mono font-bold text-slate-200">
                  Pod #{pod.index + 1}
                </div>
                <div className="text-[9px] font-mono text-slate-400">
                  {pod.state}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
