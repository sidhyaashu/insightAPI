"use client";

import { use } from "react";
import { useState, useEffect } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import Link from "next/link";

export default function CrawlLiveStreamPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const [logs, setLogs] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("connecting");
  const [capturedCount, setCapturedCount] = useState<number>(0);

  const { isConnected, lastMessage } = useWebSocket(`/crawls/${sessionId}/stream`);

  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "connected") {
      setStatus("running");
    } else if (lastMessage.type === "log") {
      setLogs((prev) => [...prev, lastMessage]);
      if (lastMessage.endpoints_found !== undefined) {
        setCapturedCount(lastMessage.endpoints_found);
      }
    } else if (lastMessage.type === "complete") {
      setStatus("completed");
      if (lastMessage.captured_count !== undefined) {
        setCapturedCount(lastMessage.captured_count);
      }
    } else if (lastMessage.type === "error") {
      setStatus("error");
      setLogs((prev) => [...prev, { type: "error", message: lastMessage.message }]);
    }
  }, [lastMessage]);

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight">Live Crawl Stream</h1>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                status === "completed"
                  ? "bg-green-500/10 text-green-500"
                  : status === "running"
                  ? "bg-blue-500/10 text-blue-500 animate-pulse"
                  : "bg-amber-500/10 text-amber-500"
              }`}
            >
              {status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs font-mono text-muted-foreground">Session ID: {sessionId}</p>
        </div>

        {status === "completed" && (
          <Link
            href={`/reports/${sessionId}`}
            className="bg-primary text-primary-foreground text-xs px-4 py-2 rounded-lg font-medium"
          >
            View Generated Specs &rarr;
          </Link>
        )}
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="border p-4 rounded-xl bg-card">
          <div className="text-xs text-muted-foreground mb-1">WebSocket Status</div>
          <div className="font-semibold text-sm">
            {isConnected ? "Connected (Live)" : "Disconnected"}
          </div>
        </div>
        <div className="border p-4 rounded-xl bg-card">
          <div className="text-xs text-muted-foreground mb-1">Endpoints Captured</div>
          <div className="font-extrabold text-xl">{capturedCount}</div>
        </div>
        <div className="border p-4 rounded-xl bg-card">
          <div className="text-xs text-muted-foreground mb-1">Log Events</div>
          <div className="font-extrabold text-xl">{logs.length}</div>
        </div>
      </div>

      {/* Terminal Log Console */}
      <div className="border border-border rounded-xl bg-black text-green-400 font-mono text-xs p-4 h-[450px] overflow-y-auto flex flex-col gap-1">
        <div className="text-gray-500 mb-2">--- Live Agent Logs Stream ---</div>
        {logs.length === 0 ? (
          <div className="text-gray-600">Waiting for agent events...</div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="flex gap-2">
              <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span>
              {log.type === "error" ? (
                <span className="text-red-400">{log.message}</span>
              ) : (
                <span>{log.message || JSON.stringify(log)}</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
