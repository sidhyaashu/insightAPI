"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  IconBrain,
  IconBolt,
  IconCoins,
  IconActivity,
  IconRefresh,
  IconChartBar,
  IconServer,
  IconRoute,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { intelligenceApi, CostsSummaryResponse, CostBreakdownItem } from "@/features/intelligence/api/intelligence.api";
import { securityApi, SecurityTestPatternItem } from "@/features/security/api/security.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function PlatformIntelligencePage() {
  const [summary, setSummary] = useState<CostsSummaryResponse | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdownItem[]>([]);
  const [patterns, setPatterns] = useState<SecurityTestPatternItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sumRes, breakRes, patRes] = await Promise.allSettled([
        intelligenceApi.getCostsSummary(),
        intelligenceApi.getCostBreakdown(),
        securityApi.listPatterns(),
      ]);

      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
      if (breakRes.status === "fulfilled") setBreakdown(breakRes.value.breakdown || []);
      if (patRes.status === "fulfilled") setPatterns(patRes.value.patterns || []);
    } catch {
      toast.error("Failed to load intelligence metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const learnedCount = patterns.filter((p) => p.status === "learned").length;
  const inReviewCount = patterns.filter((p) => p.status === "needs_review").length;

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto w-full font-sans">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20">
            <IconBrain className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Platform Intelligence & Memory Engine</h1>
            <p className="text-xs text-muted-foreground">
              Cross-target pattern memory, zero-token cache replay analytics & cumulative LLM cost reduction.
            </p>
          </div>
        </div>

        <Button variant="outline" size="sm" onClick={loadData} disabled={loading} className="text-xs gap-1.5">
          <IconRefresh className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Memory Replay Rate</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 flex items-center gap-2">
            <IconBolt className="size-5 text-emerald-400" />
            {summary ? `${summary.cache_hit_rate_pct.toFixed(1)}%` : "0.0%"}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Zero-token executions</div>
        </div>

        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Tokens Processed</div>
          <div className="text-2xl font-bold font-mono text-foreground">
            {summary ? summary.total_tokens.toLocaleString() : 0}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Across all agent nodes</div>
        </div>

        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Total LLM Invocations</div>
          <div className="text-2xl font-bold font-mono text-primary">
            {summary ? summary.total_calls.toLocaleString() : 0}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">
            {summary?.total_cached_calls || 0} resolved from memory
          </div>
        </div>

        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Total AI Spend</div>
          <div className="text-2xl font-bold font-mono text-foreground flex items-center gap-1.5">
            <IconCoins className="size-5 text-amber-500" />
            ${summary ? summary.total_spend_usd.toFixed(4) : "0.0000"}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Actual provider cost</div>
        </div>
      </div>

      {/* Model Tier & Node Spend Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
          <div className="p-4 border-b border-border/40 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <IconChartBar className="size-4 text-primary" /> Per-Node LLM Spend & Token Ledger
            </h2>
          </div>

          <div className="p-4 space-y-3 font-mono text-xs">
            {breakdown.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">No usage recorded yet.</div>
            ) : (
              breakdown.map((item, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-muted/30 border border-border/40 flex items-center justify-between gap-3">
                  <div className="space-y-0.5">
                    <div className="font-bold text-foreground">{item.node_name}</div>
                    <div className="text-[10px] text-muted-foreground">Model: {item.model}</div>
                  </div>
                  <div className="text-right space-y-0.5">
                    <div className="font-bold text-foreground">${item.total_cost_usd.toFixed(4)}</div>
                    <div className="text-[10px] text-muted-foreground">{item.total_tokens.toLocaleString()} tokens</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Pattern Generalization Status */}
        <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
          <div className="p-4 border-b border-border/40 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <IconRoute className="size-4 text-primary" /> Knowledge Promotion Funnel
            </h2>
            <div className="flex items-center gap-2">
              <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-[10px]">
                {learnedCount} Learned
              </Badge>
              <Badge variant="outline" className="text-[10px]">
                {inReviewCount} In Review
              </Badge>
            </div>
          </div>

          <div className="p-5 space-y-4 text-xs font-mono">
            <div className="p-4 rounded-xl bg-muted/20 border border-border/40 space-y-2">
              <div className="font-bold text-foreground flex items-center gap-2">
                <IconBolt className="size-4 text-emerald-400" />
                Conservative False-Negative Promotion Gate
              </div>
              <p className="text-[11px] text-muted-foreground font-sans leading-relaxed">
                Patterns require <strong>20 confirmed occurrences</strong> across at least <strong>15 distinct verified target domains</strong> and <strong>≥80% confidence</strong> before enabling zero-token cache replay. Destructive patterns are permanently restricted from automatic promotion.
              </p>
            </div>

            <div className="space-y-2 pt-2">
              <div className="flex justify-between text-muted-foreground text-[11px]">
                <span>Active Knowledge Base Size</span>
                <span className="font-bold text-foreground">{patterns.length} generalized patterns</span>
              </div>
              <div className="flex justify-between text-muted-foreground text-[11px]">
                <span>Cache Hits Avoided LLM Spend</span>
                <span className="font-bold text-emerald-400">~{summary?.total_cached_calls || 0} smart calls saved</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
