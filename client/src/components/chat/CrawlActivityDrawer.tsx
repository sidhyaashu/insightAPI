"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
  ChainOfThoughtContent,
} from "@/components/ui/chain-of-thought";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ZapIcon,
  BrainIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  GlobeIcon,
  FileCodeIcon,
  SparklesIcon,
  ActivityIcon,
  CheckCircle2Icon,
  AlertTriangleIcon,
  CoinsIcon,
  ArrowRightIcon,
  CheckIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";
import { securityApi } from "@/features/security/api/security.api";

export interface CrawlEventItem {
  id: string;
  type:
    | "connected"
    | "log"
    | "page_visited"
    | "endpoint_captured"
    | "form_submitted"
    | "vision_fallback"
    | "humanized_action"
    | "pattern_cache_hit"
    | "pattern_llm_reasoning"
    | "security_test_running"
    | "security_test_outcome"
    | "approval_required"
    | "cost_update"
    | "pending_review"
    | "complete"
    | "error";
  timestamp: number;
  data: Record<string, any>;
}

interface CrawlActivityDrawerProps {
  sessionId: string | null;
  targetUrl: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCrawlComplete?: (sessionId: string) => void;
}

export function CrawlActivityDrawer({
  sessionId,
  targetUrl,
  open,
  onOpenChange,
  onCrawlComplete,
}: CrawlActivityDrawerProps) {
  const [events, setEvents] = useState<CrawlEventItem[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<any | null>(null);
  const [approving, setApproving] = useState(false);
  const [activeCost, setActiveCost] = useState({
    tokens: 0,
    costUsd: 0,
    cacheHits: 0,
  });

  // Connect to the specific crawl WebSocket stream via Redis
  const { isConnected, lastMessage } = useWebSocket(
    sessionId ? `/ws/crawls/${sessionId}/stream` : null
  );

  // Reset state when a new session starts
  useEffect(() => {
    if (sessionId) {
      setEvents([]);
      setIsCompleted(false);
      setPendingApproval(null);
      setActiveCost({ tokens: 0, costUsd: 0, cacheHits: 0 });
    }
  }, [sessionId]);

  // Ingest streaming events
  useEffect(() => {
    if (!lastMessage) return;

    const eventType = lastMessage.type || "log";
    const newEvent: CrawlEventItem = {
      id: `evt-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      type: eventType,
      timestamp: Date.now(),
      data: lastMessage,
    };

    setEvents((prev) => [...prev, newEvent]);

    if (eventType === "cost_update") {
      setActiveCost((prev) => ({
        tokens: lastMessage.total_tokens ?? prev.tokens,
        costUsd: lastMessage.total_cost_usd ?? prev.costUsd,
        cacheHits: prev.cacheHits,
      }));
    } else if (eventType === "pattern_cache_hit") {
      setActiveCost((prev) => ({
        ...prev,
        cacheHits: prev.cacheHits + 1,
      }));
    } else if (eventType === "approval_required") {
      setPendingApproval(lastMessage);
      toast.warning("Destructive test approval required!", {
        description: `${lastMessage.method} ${lastMessage.endpoint} requires authorization.`,
      });
    } else if (eventType === "complete" || eventType === "pending_review") {
      setIsCompleted(true);
      if (sessionId) onCrawlComplete?.(sessionId);
    }
  }, [lastMessage, sessionId, onCrawlComplete]);

  // Handle destructive approval execution
  const handleApprove = async () => {
    if (!pendingApproval?.approval_id) return;
    setApproving(true);
    try {
      await securityApi.approveRun(pendingApproval.approval_id);
      toast.success("Single-use destructive test approved!");
      setPendingApproval(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Approval failed.");
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!pendingApproval?.approval_id) return;
    try {
      await securityApi.rejectApproval(pendingApproval.approval_id);
      toast.info("Destructive test cancelled.");
      setPendingApproval(null);
    } catch {
      setPendingApproval(null);
    }
  };

  const capturedEndpointsCount = useMemo(
    () => events.filter((e) => e.type === "endpoint_captured").length,
    [events]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] p-0 rounded-2xl bg-card text-card-foreground border border-border shadow-2xl flex flex-col overflow-hidden">
        {/* Header with target URL & Live metrics */}
        <DialogHeader className="p-5 border-b border-border/40 bg-muted/20 shrink-0">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <DialogTitle className="text-base font-bold flex items-center gap-2">
                  <ActivityIcon className="size-4 text-primary animate-pulse" />
                  Live Agentic Exploration Stream
                </DialogTitle>
                <Badge
                  variant="outline"
                  className={`text-[10px] font-mono px-2 py-0.5 ${
                    isCompleted
                      ? "border-emerald-500/40 text-emerald-500 bg-emerald-500/10"
                      : "border-primary/40 text-primary bg-primary/10 animate-pulse"
                  }`}
                >
                  {isCompleted ? "COMPLETED" : isConnected ? "EXPLORING" : "CONNECTING"}
                </Badge>
              </div>
              <DialogDescription className="text-xs text-muted-foreground font-mono truncate max-w-lg">
                Target: {targetUrl}
              </DialogDescription>
            </div>

            {/* Live Cost & Token Ticker */}
            <div className="flex items-center gap-3 bg-muted/40 px-3 py-1.5 rounded-xl border border-border/60 text-xs font-mono">
              <div className="flex items-center gap-1 text-muted-foreground">
                <CoinsIcon className="size-3.5 text-amber-500" />
                <span>${activeCost.costUsd.toFixed(4)}</span>
              </div>
              <div className="h-3 w-px bg-border/60" />
              <div className="text-muted-foreground">
                <span>{activeCost.tokens.toLocaleString()} tokens</span>
              </div>
              <div className="h-3 w-px bg-border/60" />
              <div className="flex items-center gap-1 text-emerald-500 font-semibold">
                <ZapIcon className="size-3 text-emerald-500" />
                <span>{activeCost.cacheHits} memory hits</span>
              </div>
            </div>
          </div>
        </DialogHeader>

        {/* Pending Approval Sticky Banner (Actionable Alert) */}
        {pendingApproval && (
          <div className="bg-amber-500/10 border-b border-amber-500/30 p-4 shrink-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-in fade-in">
            <div className="flex items-start gap-2.5 text-xs text-foreground">
              <ShieldAlertIcon className="size-4 text-amber-500 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <div className="font-semibold text-amber-400">
                  Human Approval Required: Destructive Test Proposal
                </div>
                <div className="text-muted-foreground font-mono text-[11px]">
                  {pendingApproval.method} {pendingApproval.endpoint} &bull; Class: {pendingApproval.vuln_class}
                </div>
                <p className="text-[11px] text-muted-foreground italic">
                  "{pendingApproval.reasoning_trace}"
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                size="sm"
                variant="outline"
                onClick={handleReject}
                className="h-7 text-xs px-2 text-muted-foreground hover:text-foreground"
              >
                <XIcon className="size-3 mr-1" /> Dismiss
              </Button>
              <Button
                size="sm"
                onClick={handleApprove}
                disabled={approving}
                className="h-7 text-xs px-3 bg-amber-500 hover:bg-amber-600 text-black font-semibold"
              >
                <CheckIcon className="size-3 mr-1" />
                {approving ? "Authorizing..." : "Approve Single Run"}
              </Button>
            </div>
          </div>
        )}

        {/* Real-Time Event Feed using Chain-of-Thought Patterns */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 font-sans text-xs">
          <ChainOfThought defaultOpen={true}>
            <ChainOfThoughtHeader className="font-mono text-xs text-muted-foreground pb-2 border-b border-border/40">
              Autonomous Agent Actions & Decision Trace ({events.length} events)
            </ChainOfThoughtHeader>

            <ChainOfThoughtContent className="space-y-3 pt-2">
              {events.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground font-mono animate-pulse">
                  Waiting for initial browser interaction events...
                </div>
              ) : (
                events.map((evt) => {
                  switch (evt.type) {
                    case "page_visited":
                      return (
                        <ChainOfThoughtStep
                          key={evt.id}
                          icon={GlobeIcon}
                          label={
                            <div className="flex items-center gap-2 font-mono">
                              <span className="font-bold text-foreground">Navigated to Page {evt.data.page_number}</span>
                              <Badge variant="outline" className="text-[9px] px-1 py-0 border-blue-500/30 text-blue-400">
                                {evt.data.interactive_count} interactive controls
                              </Badge>
                            </div>
                          }
                          description={<span className="font-mono text-[11px]">{evt.data.url}</span>}
                          status="complete"
                        />
                      );

                    case "pattern_cache_hit":
                      return (
                        <div
                          key={evt.id}
                          className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 flex items-start gap-3 text-xs animate-in fade-in"
                        >
                          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 shrink-0">
                            <ZapIcon className="size-4" />
                          </div>
                          <div className="space-y-0.5 flex-1 font-mono text-[11px]">
                            <div className="flex items-center gap-2 font-bold text-emerald-400">
                              <span>⚡ Resolved Instantly from Memory</span>
                              <Badge className="bg-emerald-500 text-black text-[9px] px-1.5 py-0 font-bold">
                                0 Tokens Billed
                              </Badge>
                            </div>
                            <div className="text-foreground">{evt.data.endpoint}</div>
                            <div className="text-muted-foreground text-[10px]">
                              Reused learned pattern (tested {evt.data.occurrences}x across {evt.data.distinct_targets} domains with {Math.round((evt.data.confidence || 0.8) * 100)}% confidence).
                            </div>
                          </div>
                        </div>
                      );

                    case "pattern_llm_reasoning":
                      return (
                        <div
                          key={evt.id}
                          className="p-3 rounded-xl border border-purple-500/30 bg-purple-500/5 flex items-start gap-3 text-xs animate-in fade-in"
                        >
                          <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 shrink-0 animate-pulse">
                            <BrainIcon className="size-4" />
                          </div>
                          <div className="space-y-0.5 flex-1 font-mono text-[11px]">
                            <div className="flex items-center gap-2 font-bold text-purple-400">
                              <span>🧠 LLM Reasoning & Strategy Synthesis</span>
                              <Badge variant="outline" className="border-purple-500/30 text-purple-300 text-[9px] px-1.5 py-0">
                                {evt.data.model || "GPT-4o"}
                              </Badge>
                            </div>
                            <div className="text-foreground">{evt.data.endpoint}</div>
                            <div className="text-muted-foreground text-[10px]">
                              Reason: {evt.data.reason || "Novel endpoint structure requiring test case generation"}.
                            </div>
                          </div>
                        </div>
                      );

                    case "security_test_running":
                      return (
                        <ChainOfThoughtStep
                          key={evt.id}
                          icon={ShieldCheckIcon}
                          label={
                            <div className="flex items-center gap-2 font-mono">
                              <span className="font-bold text-foreground">Sandbox Security Probe</span>
                              <Badge variant="outline" className="text-[9px] uppercase px-1.5 py-0 text-amber-400 border-amber-500/30">
                                {evt.data.vuln_class}
                              </Badge>
                              {evt.data.is_cache_hit && (
                                <Badge className="bg-emerald-500/20 text-emerald-400 text-[9px] px-1 py-0">
                                  Cached Replay
                                </Badge>
                              )}
                            </div>
                          }
                          description={<span className="font-mono text-[11px]">{evt.data.method} {evt.data.endpoint}</span>}
                          status="active"
                        />
                      );

                    case "security_test_outcome":
                      return (
                        <ChainOfThoughtStep
                          key={evt.id}
                          icon={evt.data.outcome === "vulnerable" ? ShieldAlertIcon : CheckCircle2Icon}
                          label={
                            <div className="flex items-center gap-2 font-mono">
                              <span className="font-bold">
                                Outcome:{" "}
                                <strong
                                  className={
                                    evt.data.outcome === "vulnerable"
                                      ? "text-rose-400"
                                      : evt.data.outcome === "not_vulnerable"
                                      ? "text-emerald-400"
                                      : "text-muted-foreground"
                                  }
                                >
                                  {evt.data.outcome.toUpperCase()}
                                </strong>
                              </span>
                              <Badge variant="outline" className="text-[9px] font-mono px-1 py-0">
                                {evt.data.vuln_class}
                              </Badge>
                            </div>
                          }
                          description={<span className="font-mono text-[11px]">{evt.data.method} {evt.data.endpoint}</span>}
                          status="complete"
                        />
                      );

                    case "endpoint_captured":
                      return (
                        <ChainOfThoughtStep
                          key={evt.id}
                          icon={FileCodeIcon}
                          label={
                            <div className="flex items-center gap-2 font-mono">
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1 py-0 ${
                                  evt.data.method === "GET"
                                    ? "text-blue-400 border-blue-500/30"
                                    : "text-emerald-400 border-emerald-500/30"
                                }`}
                              >
                                {evt.data.method}
                              </Badge>
                              <span className="font-bold text-foreground truncate">{evt.data.template_route || evt.data.url}</span>
                            </div>
                          }
                          description={<span className="font-mono text-[10px] text-muted-foreground">Status: {evt.data.status} &bull; Type: {evt.data.resource_type}</span>}
                          status="complete"
                        />
                      );

                    default:
                      return (
                        <ChainOfThoughtStep
                          key={evt.id}
                          icon={ActivityIcon}
                          label={<span className="text-foreground">{evt.data.message || "Agent activity logged"}</span>}
                          status="complete"
                        />
                      );
                  }
                })
              )}
            </ChainOfThoughtContent>
          </ChainOfThought>
        </div>

        {/* Footer with Completion Actions */}
        <div className="p-4 border-t border-border/40 bg-muted/20 flex items-center justify-between gap-3 shrink-0">
          <div className="text-xs text-muted-foreground font-mono">
            {capturedEndpointsCount} API endpoints captured
          </div>

          <div className="flex items-center gap-2">
            {isCompleted && sessionId && (
              <Link href={`/crawls/${sessionId}/review`}>
                <Button size="sm" className="gap-1.5 text-xs bg-primary text-primary-foreground font-semibold">
                  <span>Review Schemas & Export</span>
                  <ArrowRightIcon className="size-3.5" />
                </Button>
              </Link>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
