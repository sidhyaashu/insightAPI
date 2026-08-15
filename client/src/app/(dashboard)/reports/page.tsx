"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  IconGitCompare,
  IconSparkles,
  IconRefresh,
  IconAlertTriangle,
  IconCircleCheck,
  IconClock,
  IconLoader,
  IconArrowRight,
  IconListCheck,
  IconGlobe,
} from "@tabler/icons-react";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import type { CrawlSession } from "@/lib/api-client/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function ReportsOverviewPage() {
  const [crawls, setCrawls] = useState<CrawlSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCrawls = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await crawlsApi.listCrawls(50, 0);
      setCrawls(list);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load crawls.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCrawls();
  }, [loadCrawls]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-muted-foreground min-h-[60vh]">
        <div className="size-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <span className="text-sm font-mono">Loading crawl reports…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-4 p-8 text-center min-h-[60vh]">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
          <IconAlertTriangle className="size-6 text-destructive" />
        </div>
        <p className="text-sm font-semibold text-foreground">Failed to load reports</p>
        <Button variant="outline" size="sm" onClick={loadCrawls} className="gap-2">
          <IconRefresh className="size-4" />
          Retry
        </Button>
      </div>
    );
  }

  const completedCount = crawls.filter((c) => c.status === "completed").length;
  const reviewCount = crawls.filter((c) => c.status === "pending_review").length;
  const runningCount = crawls.filter((c) => c.status === "running").length;

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto w-full font-sans pb-28">
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs">
            <IconGlobe className="size-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Crawl Reports & API Intelligence
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Review captured endpoints, approve specifications, export OpenAPI/Postman artifacts, and compare schema drift across crawls.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadCrawls} className="gap-1.5 text-xs h-8">
            <IconRefresh className="size-3.5" /> Refresh
          </Button>
          <Link href="/chat">
            <Button size="sm" className="gap-1.5 text-xs bg-primary text-primary-foreground font-semibold h-8 shadow-xs">
              <IconSparkles className="size-3.5" /> Start Crawl
            </Button>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Total Crawls</div>
          <div className="text-2xl font-extrabold font-mono text-foreground">{crawls.length}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Exploration sessions</div>
        </div>
        <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 shadow-xs">
          <div className="text-[11px] text-emerald-500 font-mono uppercase mb-1">Completed Specifications</div>
          <div className="text-2xl font-extrabold font-mono text-emerald-400">{completedCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">OpenAPI 3.1 ready</div>
        </div>
        <div className="p-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 shadow-xs">
          <div className="text-[11px] text-amber-500 font-mono uppercase mb-1">Pending Human Review</div>
          <div className="text-2xl font-extrabold font-mono text-amber-400">{reviewCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Awaiting schema approval</div>
        </div>
        <div className="p-4 rounded-2xl border border-blue-500/20 bg-blue-500/5 shadow-xs">
          <div className="text-[11px] text-blue-400 font-mono uppercase mb-1">Running / Processing</div>
          <div className="text-2xl font-extrabold font-mono text-blue-400">{runningCount}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Active crawler agents</div>
        </div>
      </div>

      {crawls.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-center rounded-2xl border border-dashed border-border bg-card/50">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <IconGlobe className="size-6" />
          </div>
          <p className="text-sm font-semibold text-foreground">No crawls yet</p>
          <p className="text-xs text-muted-foreground max-w-xs">
            Start a crawl in the AI Chatbot workspace to discover endpoints and generate OpenAPI specs.
          </p>
          <Link href="/chat">
            <Button size="sm" className="gap-1.5 text-xs bg-primary text-primary-foreground font-semibold">
              <IconSparkles className="size-3.5" />
              Start Crawl in Chat
            </Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {crawls.map((crawl) => {
            const isPendingReview = crawl.status === "pending_review";
            const isCompleted = crawl.status === "completed";
            const isRunning = crawl.status === "running";
            const isFailed = crawl.status === "failed";

            return (
              <div
                key={crawl.session_id}
                className="rounded-2xl border border-border/70 bg-card p-5 shadow-xs hover:border-border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-bold text-sm text-foreground truncate max-w-md">
                      {crawl.target_url}
                    </span>

                    {isPendingReview && (
                      <Badge
                        variant="outline"
                        className="gap-1 bg-amber-500/10 text-amber-400 border-amber-500/30 text-[10px] font-mono"
                      >
                        <IconClock className="size-3" />
                        Pending Review
                      </Badge>
                    )}

                    {isCompleted && (
                      <Badge
                        variant="outline"
                        className="gap-1 bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-[10px] font-mono"
                      >
                        <IconCircleCheck className="size-3" />
                        Completed
                      </Badge>
                    )}

                    {isRunning && (
                      <Badge
                        variant="outline"
                        className="gap-1 bg-blue-500/10 text-blue-400 border-blue-500/30 text-[10px] font-mono"
                      >
                        <IconLoader className="size-3 animate-spin" />
                        Crawling…
                      </Badge>
                    )}

                    {isFailed && (
                      <Badge
                        variant="outline"
                        className="gap-1 bg-rose-500/10 text-rose-400 border-rose-500/30 text-[10px] font-mono"
                      >
                        <IconAlertTriangle className="size-3" />
                        Failed
                      </Badge>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground flex-wrap">
                    <span>
                      Captured: <strong className="text-foreground">{crawl.captured_count}</strong> endpoints
                    </span>
                    <span>·</span>
                    <span>Max Pages: {crawl.max_pages}</span>
                    <span>·</span>
                    <span>{new Date(crawl.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {isPendingReview && (
                    <Link href={`/crawls/${crawl.session_id}/review`}>
                      <Button size="sm" className="gap-1.5 text-xs bg-amber-500 hover:bg-amber-600 text-black font-semibold">
                        <IconListCheck className="size-3.5" />
                        Review Endpoints
                        <IconArrowRight className="size-3" />
                      </Button>
                    </Link>
                  )}

                  {isCompleted && (
                    <>
                      <Link href={`/reports/${crawl.session_id}`}>
                        <Button variant="outline" size="sm" className="text-xs gap-1.5 border-primary/40 text-primary hover:bg-primary/10">
                          <IconSparkles className="size-3.5" />
                          Report & Tests
                        </Button>
                      </Link>
                      <Link href={`/crawls/${crawl.session_id}/review`}>
                        <Button variant="outline" size="sm" className="text-xs gap-1.5">
                          <IconListCheck className="size-3.5" />
                          View Schema
                        </Button>
                      </Link>
                      <Link href={`/reports/${crawl.session_id}/drift`}>
                        <Button size="sm" variant="default" className="text-xs gap-1.5 bg-primary text-primary-foreground font-semibold">
                          <IconGitCompare className="size-3.5" />
                          Drift Diff
                        </Button>
                      </Link>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
