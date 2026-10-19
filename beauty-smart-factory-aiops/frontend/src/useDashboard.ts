import { useCallback, useEffect, useRef, useState } from "react";
import type { DashboardSnapshot, ScenarioId } from "./types";

export type ConnState = "connecting" | "open" | "closed";

function wsUrl(): string {
  const override = import.meta.env.VITE_WS_URL as string | undefined;
  if (override) return override;
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/dashboard`;
}

function apiBase(): string {
  return (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
}

/** `/ws/dashboard` 0.5초 스트림 구독 + 자동 재연결 */
export function useDashboard() {
  const [snap, setSnap] = useState<DashboardSnapshot | null>(null);
  const [conn, setConn] = useState<ConnState>("connecting");
  const [pending, setPending] = useState<ScenarioId | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (disposed) return;
      setConn("connecting");
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;
      ws.onopen = () => {
        retryRef.current = 0;
        setConn("open");
      };
      ws.onmessage = (ev) => {
        try {
          setSnap(JSON.parse(ev.data) as DashboardSnapshot);
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        setConn("closed");
        if (disposed) return;
        const delay = Math.min(5000, 500 * 2 ** retryRef.current++);
        timer = setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      wsRef.current?.close();
    };
  }, []);

  const trigger = useCallback(async (id: ScenarioId) => {
    setPending(id);
    try {
      const res = await fetch(`${apiBase()}/api/scenario/${id}`, { method: "POST" });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      // REST 실패 시 WebSocket 채널로 폴백
      wsRef.current?.send(JSON.stringify({ scenario: id }));
    } finally {
      setTimeout(() => setPending(null), 400);
    }
  }, []);

  return { snap, conn, trigger, pending };
}
