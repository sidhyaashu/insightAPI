"use client";

import { use, useState, useEffect } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";

export default function CrawlLiveStreamPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const [logs, setLogs] = useState<any[]>([]);
  const [status, setStatus] = useState<string>("connecting");
  const [capturedCount, setCapturedCount] = useState<number>(0);
  const [targetUrl, setTargetUrl] = useState<string>("");

  const { isConnected, lastMessage } = useWebSocket(`/crawls/${sessionId}/stream`);

  // Hydrate initial REST state on mount
  useEffect(() => {
    async function hydrateCrawlState() {
      try {
        const session = await crawlsApi.getCrawlById(sessionId);
        if (session) {
          setStatus(session.status);
          setCapturedCount(session.captured_count);
          setTargetUrl(session.target_url);
        }
      } catch {}
    }
    hydrateCrawlState();
  }, [sessionId]);

  // Listen for live WebSocket stream events
  useEffect(() => {
    if (!lastMessage) return;

    const timestamp = new Date().toISOString().substring(11, 19);

    if (lastMessage.type === "connected") {
      setStatus((prev) => (prev === "completed" ? "completed" : "running"));
    } else if (lastMessage.type === "log") {
      setLogs((prev) => [...prev, { ...lastMessage, formatted_time: timestamp }]);
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
      setLogs((prev) => [...prev, { type: "error", message: lastMessage.message, formatted_time: timestamp }]);
    }
  }, [lastMessage]);

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6 font-sans">
      <div className="flex justify-between items-center pb-3 border-b border-border/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold tracking-tight">Live Crawl Stream</h1>
            <Badge
              variant="outline"
              className={`text-xs px-2.5 py-0.5 rounded-full font-mono ${
                status === "completed"
                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                  : status === "running"
                  ? "bg-blue-500/10 text-blue-500 border-blue-500/30 animate-pulse"
                  : "bg-amber-500/10 text-amber-500 border-amber-500/30"
              }`}
            >
              {status.toUpperCase()}
            </Badge>
          </div>
          <p className="text-xs font-mono text-muted-foreground">
            Session ID: {sessionId} {targetUrl && `| Target: ${targetUrl}`}
          </p>
        </div>

        {status === "completed" && (
          <Link
            href={`/reports/${sessionId}`}
            className="bg-primary text-primary-foreground text-xs px-4 py-2 rounded-lg font-medium hover:opacity-90 transition"
          >
            View Generated Specs &rarr;
          </Link>
        )}
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="border border-border/60 p-4 rounded-xl bg-card shadow-xs">
          <div className="text-xs text-muted-foreground mb-1 font-mono">WebSocket Status</div>
          <div className="font-semibold text-sm flex items-center gap-2">
            <span className={`size-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-muted-foreground/40"}`} />
            <span>{isConnected ? "Connected (Live)" : "Disconnected"}</span>
          </div>
        </div>
        <div className="border border-border/60 p-4 rounded-xl bg-card shadow-xs">
          <div className="text-xs text-muted-foreground mb-1 font-mono">Endpoints Captured</div>
          <div className="font-extrabold text-xl font-mono text-foreground">{capturedCount}</div>
        </div>
        <div className="border border-border/60 p-4 rounded-xl bg-card shadow-xs">
          <div className="text-xs text-muted-foreground mb-1 font-mono">Log Events</div>
          <div className="font-extrabold text-xl font-mono text-foreground">{logs.length}</div>
        </div>
      </div>

      {/* Terminal Log Console */}
      <div className="border border-border/80 rounded-xl bg-[#121210] text-emerald-400 font-mono text-xs p-4 h-[420px] overflow-y-auto flex flex-col gap-1 shadow-inner">
        <div className="text-muted-foreground/60 mb-2">--- Live Agent Execution Logs ---</div>
        {logs.length === 0 ? (
          <div className="text-muted-foreground/40">Waiting for live agent events...</div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="flex gap-2">
              <span className="text-muted-foreground/50">[{log.formatted_time || "00:00:00"}]</span>
              {log.type === "error" ? (
                <span className="text-destructive font-semibold">{log.message}</span>
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
