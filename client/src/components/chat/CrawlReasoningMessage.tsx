"use client";

/**
 * CrawlReasoningMessage
 *
 * Inline assistant-style component that renders inside the conversation thread
 * matching Claude.ai's left-side reasoning pattern:
 *
 *   LEFT (chat thread) = live chain-of-thought execution steps
 *   RIGHT (ArtifactPanel) = final output artifacts only
 *
 * Event rendering:
 *   pattern_cache_hit      -> muted emerald row, no pulse (instant / cost-free)
 *   pattern_llm_reasoning  -> <ReasoningBlock> collapsible with isStreaming=true
 *   security_test_running  -> ChainOfThoughtStep status="active"
 *   security_test_outcome  -> color-coded complete row
 *   sandbox_action         -> amber [SANDBOXED] badge + probe description
 *   approval_required      -> sticky non-dismissible approval banner
 *   page_visited / endpoint_captured -> standard ChainOfThoughtStep
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useCrawlActivity } from "./CrawlActivityContext";
import { ReasoningBlock } from "./ReasoningBlock";
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtContent,
  ChainOfThoughtStep,
} from "@/components/ui/chain-of-thought";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ZapIcon,
  BrainIcon,
  ShieldAlertIcon,
  ShieldCheckIcon,
  GlobeIcon,
  FileCodeIcon,
  ActivityIcon,
  CheckCircle2Icon,
  CoinsIcon,
  ArrowRightIcon,
  CheckIcon,
  XIcon,
  BoxIcon,
  Loader2Icon,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function CostTicker({
  tokens,
  costUsd,
  cacheHits,
}: {
  tokens: number;
  costUsd: number;
  cacheHits: number;
}) {
  return (
    <div className="flex items-center gap-2.5 bg-muted/40 px-2.5 py-1 rounded-lg border border-border/50 text-[10px] font-mono shrink-0">
      <div className="flex items-center gap-1 text-muted-foreground">
        <CoinsIcon className="size-3 text-amber-500" />
        <span>${costUsd.toFixed(4)}</span>
      </div>
      <div className="h-2.5 w-px bg-border/60" />
      <div className="text-muted-foreground">
        {tokens.toLocaleString()} tok
      </div>
      <div className="h-2.5 w-px bg-border/60" />
      <div className="flex items-center gap-1 text-emerald-500 font-semibold">
        <ZapIcon className="size-2.5" />
        <span>{cacheHits} cached</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CrawlReasoningMessage() {
  const {
    sessionId,
    targetUrl,
    events,
    isCompleted,
    isConnected,
    activeCost,
    pendingApproval,
    approving,
    handleApprove,
    handleReject,
    clearCrawlSession,
  } = useCrawlActivity();

  // Auto-scroll the event list to bottom as events arrive
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  // Track which LLM reasoning events are still "streaming" (no follow-up probe yet)
  const completedLlmEndpoints = useMemo(() => {
    const completed = new Set<string>();
    events.forEach((evt) => {
      if (evt.type === "security_test_running" && evt.data.endpoint) {
        completed.add(evt.data.endpoint);
      }
    });
    return completed;
  }, [events]);

  const capturedCount = useMemo(
    () => events.filter((e) => e.type === "endpoint_captured").length,
    [events]
  );

  if (!sessionId) return null;

  const statusLabel = isCompleted
    ? "COMPLETED"
    : isConnected
    ? "EXPLORING"
    : "CONNECTING";

  return (
    <div className="w-full space-y-2 font-sans">
      {/* --- Main collapsible reasoning block --- */}
      <ChainOfThought defaultOpen={true}>
        {/* Header: matches ChainOfThoughtHeader style but with live status */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <ChainOfThoughtHeader className="flex-1">
            <span className="flex items-center gap-2">
              {!isCompleted && isConnected ? (
                <Loader2Icon className="size-3.5 text-primary animate-spin shrink-0" />
              ) : null}
              Live Execution{" "}
              <span className="text-muted-foreground font-normal">
                &middot; {events.length} events
              </span>
            </span>
            <Badge
              variant="outline"
              className={cn(
                "text-[9px] font-mono px-1.5 py-0 h-4 ml-1 shrink-0",
                isCompleted
                  ? "border-emerald-500/40 text-emerald-500 bg-emerald-500/10"
                  : "border-primary/40 text-primary bg-primary/10 animate-pulse"
              )}
            >
              {statusLabel}
            </Badge>
          </ChainOfThoughtHeader>

          <CostTicker
            tokens={activeCost.tokens}
            costUsd={activeCost.costUsd}
            cacheHits={activeCost.cacheHits}
          />
        </div>

        <ChainOfThoughtContent>
          {/* --- Sticky approval banner (non-dismissible until resolved) --- */}
          {pendingApproval && (
            <div className="sticky top-0 z-10 mb-3 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-in fade-in shadow-sm">
              <div className="flex items-start gap-2.5 text-xs text-foreground">
                <ShieldAlertIcon className="size-4 text-amber-500 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <div className="font-semibold text-amber-400 text-[11px]">
                    Human Approval Required &mdash; Destructive Test
                  </div>
                  <div className="text-muted-foreground font-mono text-[10px]">
                    {pendingApproval.method} {pendingApproval.endpoint} &bull;{" "}
                    {pendingApproval.vuln_class}
                  </div>
                  {pendingApproval.reasoning_trace && (
                    <p className="text-[10px] text-muted-foreground italic max-w-sm truncate">
                      &ldquo;{pendingApproval.reasoning_trace}&rdquo;
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleReject}
                  className="h-6 text-[10px] px-2 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <XIcon className="size-3 mr-1" /> Dismiss
                </Button>
                <Button
                  size="sm"
                  onClick={handleApprove}
                  disabled={approving}
                  className="h-6 text-[10px] px-2.5 bg-amber-500 hover:bg-amber-600 text-black font-semibold cursor-pointer"
                >
                  <CheckIcon className="size-3 mr-1" />
                  {approving ? "Authorizing..." : "Approve"}
                </Button>
              </div>
            </div>
          )}

          {/* --- Event feed --- */}
          {events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground font-mono text-[11px] animate-pulse">
              Waiting for agent events&hellip;
            </div>
          ) : (
            <div className="space-y-1">
              {events.map((evt) => {
                switch (evt.type) {
                  // ── Cache hit: muted, no pulse, instant badge ────────────
                  case "pattern_cache_hit":
                    return (
                      <div
                        key={evt.id}
                        className="flex items-start gap-2.5 px-1 py-1.5 rounded-lg animate-in fade-in"
                      >
                        <div className="p-1 rounded-md bg-emerald-500/10 text-emerald-500 shrink-0 mt-0.5">
                          <ZapIcon className="size-3" />
                        </div>
                        <div className="flex-1 space-y-0.5 font-mono text-[11px]">
                          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                            <span>Resolved from memory</span>
                            <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-[9px] px-1.5 py-0 h-3.5 font-bold">
                              0 tokens
                            </Badge>
                          </div>
                          <div className="text-muted-foreground text-[10px] truncate">
                            {evt.data.endpoint} &bull; {evt.data.occurrences}x
                            across {evt.data.distinct_targets} domains (
                            {Math.round((evt.data.confidence || 0.8) * 100)}%
                            confidence)
                          </div>
                        </div>
                      </div>
                    );

                  // ── LLM reasoning: ReasoningBlock with isStreaming ───────
                  case "pattern_llm_reasoning":
                    return (
                      <div key={evt.id} className="px-1 py-1 animate-in fade-in">
                        <ReasoningBlock
                          reasoning={
                            evt.data.reason ||
                            "Synthesizing test cases for novel endpoint structure..."
                          }
                          isStreaming={
                            !completedLlmEndpoints.has(evt.data.endpoint)
                          }
                        />
                        <div className="ml-2 text-[10px] font-mono text-muted-foreground mt-0.5 truncate">
                          {evt.data.model && (
                            <Badge
                              variant="outline"
                              className="border-purple-500/30 text-purple-400 text-[9px] px-1 py-0 mr-1.5 h-3.5"
                            >
                              {evt.data.model}
                            </Badge>
                          )}
                          {evt.data.endpoint}
                        </div>
                      </div>
                    );

                  // ── Sandbox action: amber SANDBOXED badge ────────────────
                  case "sandbox_action":
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <BoxIcon className="size-3 text-amber-500 shrink-0" />
                            <span className="text-foreground font-medium">
                              {evt.data.method} {evt.data.url || evt.data.strategy}
                            </span>
                            <Badge
                              variant="outline"
                              className="border-amber-500/40 text-amber-400 bg-amber-500/5 text-[8px] px-1 py-0 h-3.5 uppercase tracking-wide"
                            >
                              SANDBOXED
                            </Badge>
                          </div>
                        }
                        description={
                          <span className="font-mono text-[10px]">
                            Isolated probe &bull; {evt.data.vuln_class} &bull;{" "}
                            {evt.data.action}
                          </span>
                        }
                        status="active"
                      />
                    );

                  // ── Security test running ────────────────────────────────
                  case "security_test_running":
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <span className="font-bold text-foreground">
                              Sandbox Probe
                            </span>
                            <Badge
                              variant="outline"
                              className="text-[9px] uppercase px-1 py-0 h-3.5 text-amber-400 border-amber-500/30"
                            >
                              {evt.data.vuln_class}
                            </Badge>
                            {evt.data.is_cache_hit && (
                              <Badge className="bg-emerald-500/20 text-emerald-400 text-[9px] px-1 py-0 h-3.5">
                                Cached
                              </Badge>
                            )}
                          </div>
                        }
                        description={
                          <span className="font-mono text-[10px]">
                            {evt.data.method} {evt.data.endpoint}
                          </span>
                        }
                        status="active"
                      />
                    );

                  // ── Security test outcome ────────────────────────────────
                  case "security_test_outcome":
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            {evt.data.outcome === "vulnerable" ? (
                              <ShieldAlertIcon className="size-3.5 text-rose-400 shrink-0" />
                            ) : (
                              <CheckCircle2Icon className="size-3.5 text-emerald-400 shrink-0" />
                            )}
                            <span
                              className={cn(
                                "font-bold",
                                evt.data.outcome === "vulnerable"
                                  ? "text-rose-400"
                                  : evt.data.outcome === "not_vulnerable"
                                  ? "text-emerald-400"
                                  : "text-muted-foreground"
                              )}
                            >
                              {(evt.data.outcome as string).replace(
                                "_",
                                " "
                              ).toUpperCase()}
                            </span>
                            <Badge
                              variant="outline"
                              className="text-[9px] font-mono px-1 py-0 h-3.5"
                            >
                              {evt.data.vuln_class}
                            </Badge>
                          </div>
                        }
                        description={
                          <span className="font-mono text-[10px]">
                            {evt.data.method} {evt.data.endpoint}
                            {evt.data.ran_via_cache && (
                              <Badge className="ml-1.5 bg-emerald-500/15 text-emerald-400 text-[9px] px-1 py-0 h-3.5">
                                cache replay
                              </Badge>
                            )}
                          </span>
                        }
                        status="complete"
                      />
                    );

                  // ── Page visited ─────────────────────────────────────────
                  case "page_visited":
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <GlobeIcon className="size-3 text-blue-400 shrink-0" />
                            <span className="font-medium text-foreground">
                              Page {evt.data.page_number}
                            </span>
                            {evt.data.interactive_count !== undefined && (
                              <Badge
                                variant="outline"
                                className="text-[9px] px-1 py-0 h-3.5 border-blue-500/30 text-blue-400"
                              >
                                {evt.data.interactive_count} controls
                              </Badge>
                            )}
                          </div>
                        }
                        description={
                          <span className="font-mono text-[10px] text-muted-foreground truncate block max-w-xs">
                            {evt.data.url}
                          </span>
                        }
                        status="complete"
                      />
                    );

                  // ── Endpoint captured ────────────────────────────────────
                  case "endpoint_captured":
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <div className="flex items-center gap-1.5 font-mono text-[11px]">
                            <FileCodeIcon className="size-3 shrink-0" />
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[9px] px-1 py-0 h-3.5",
                                evt.data.method === "GET"
                                  ? "text-blue-400 border-blue-500/30"
                                  : "text-emerald-400 border-emerald-500/30"
                              )}
                            >
                              {evt.data.method}
                            </Badge>
                            <span className="font-medium text-foreground truncate max-w-[200px]">
                              {evt.data.template_route || evt.data.url}
                            </span>
                          </div>
                        }
                        description={
                          <span className="font-mono text-[10px] text-muted-foreground">
                            Status: {evt.data.status} &bull;{" "}
                            {evt.data.resource_type}
                          </span>
                        }
                        status="complete"
                      />
                    );

                  // ── Default fallback ─────────────────────────────────────
                  default:
                    if (
                      evt.type === "connected" ||
                      evt.type === "cost_update"
                    )
                      return null;
                    return (
                      <ChainOfThoughtStep
                        key={evt.id}
                        label={
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {evt.data.message || evt.type}
                          </span>
                        }
                        status="complete"
                      />
                    );
                }
              })}
              <div ref={bottomRef} />
            </div>
          )}
        </ChainOfThoughtContent>
      </ChainOfThought>

      {/* --- Footer: completion actions + target --- */}
      <div className="flex items-center justify-between gap-3 pt-1 text-[11px] text-muted-foreground font-mono">
        <span className="truncate max-w-xs">{targetUrl}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span>{capturedCount} endpoints</span>
          {isCompleted && sessionId && (
            <Link href={`/crawls/${sessionId}/review`}>
              <Button
                size="sm"
                className="h-6 text-[10px] px-2.5 gap-1 bg-primary text-primary-foreground font-semibold cursor-pointer"
              >
                Review & Export
                <ArrowRightIcon className="size-3" />
              </Button>
            </Link>
          )}
          {isCompleted && (
            <Button
              size="sm"
              variant="ghost"
              onClick={clearCrawlSession}
              className="h-6 text-[10px] px-2 text-muted-foreground cursor-pointer"
            >
              Dismiss
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
