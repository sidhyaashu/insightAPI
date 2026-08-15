"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  IconShieldLock,
  IconShieldCheck,
  IconShieldExclamation,
  IconAlertTriangle,
  IconCheck,
  IconX,
  IconRefresh,
  IconPlayerPlay,
  IconFileCode,
  IconActivity,
  IconBrain,
  IconBolt,
  IconLock,
  IconExternalLink,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { securityApi, SecurityApprovalItem, SecurityFindingItem, SecurityTestPatternItem } from "@/features/security/api/security.api";
import { domainsApi } from "@/features/domains/api/domains.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SecurityCenterPage() {
  const [approvals, setApprovals] = useState<SecurityApprovalItem[]>([]);
  const [findings, setFindings] = useState<SecurityFindingItem[]>([]);
  const [patterns, setPatterns] = useState<SecurityTestPatternItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  // Selected finding modal for full evidence JSON
  const [selectedFinding, setSelectedFinding] = useState<SecurityFindingItem | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [approvalsRes, findingsRes, patternsRes] = await Promise.allSettled([
        securityApi.listPendingApprovals(),
        securityApi.listFindings(),
        securityApi.listPatterns(),
      ]);

      if (approvalsRes.status === "fulfilled") {
        setApprovals(approvalsRes.value.pending_approvals || []);
      }
      if (findingsRes.status === "fulfilled") {
        setFindings(findingsRes.value.findings || []);
      }
      if (patternsRes.status === "fulfilled") {
        setPatterns(patternsRes.value.patterns || []);
      }
    } catch {
      toast.error("Failed to load security intelligence data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleApprove = async (approvalId: string) => {
    setApprovingId(approvalId);
    try {
      await securityApi.approveRun(approvalId);
      toast.success("Single-use destructive test authorized!");
      setApprovals((prev) => prev.filter((a) => a.id !== approvalId));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Approval failed.");
    } finally {
      setApprovingId(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    try {
      await securityApi.rejectApproval(approvalId);
      toast.info("Destructive test approval rejected.");
      setApprovals((prev) => prev.filter((a) => a.id !== approvalId));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Rejection failed.");
    }
  };

  const criticalFindings = findings.filter((f) => f.severity === "critical");
  const highFindings = findings.filter((f) => f.severity === "high");
  const cachedFindings = findings.filter((f) => f.ran_via_cache);

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto w-full font-sans pb-28">
      {/* Top Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs">
            <IconShieldLock className="size-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              API Security Intelligence Center
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Adaptive memory-driven vulnerability testing, isolated sandbox execution & human-in-the-loop approvals.
            </p>
          </div>
        </div>

        <Button variant="outline" size="sm" onClick={loadData} disabled={loading} className="text-xs gap-1.5 h-8">
          <IconRefresh className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Confirmed Vulnerabilities</div>
          <div className="text-2xl font-extrabold font-mono text-foreground flex items-center gap-2">
            {findings.length}
            {criticalFindings.length > 0 && (
              <Badge className="bg-rose-500 text-white text-[10px] px-1.5 py-0 font-bold shadow-xs">
                {criticalFindings.length} Critical
              </Badge>
            )}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Discovered security findings</div>
        </div>

        <div className="p-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 shadow-xs">
          <div className="text-[11px] text-amber-400 font-mono uppercase mb-1">Pending Human Approvals</div>
          <div className="text-2xl font-extrabold font-mono text-amber-400 flex items-center gap-2">
            {approvals.length}
            {approvals.length > 0 && (
              <Badge variant="outline" className="border-amber-500/40 text-amber-400 bg-amber-500/10 text-[10px] animate-pulse font-bold">
                Action Required
              </Badge>
            )}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Destructive test proposals</div>
        </div>

        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Learned Test Patterns</div>
          <div className="text-2xl font-extrabold font-mono text-primary">
            {patterns.filter((p) => p.status === "learned").length}
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Knowledge graph signatures</div>
        </div>

        <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 shadow-xs">
          <div className="text-[11px] text-emerald-400 font-mono uppercase mb-1">Zero-Token Cache Replays</div>
          <div className="text-2xl font-extrabold font-mono text-emerald-400 flex items-center gap-1.5">
            <IconBolt className="size-5 text-emerald-400" />
            {cachedFindings.length} findings
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Instant memory execution</div>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs defaultValue={approvals.length > 0 ? "approvals" : "findings"} className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-lg">
          <TabsTrigger value="approvals" className="text-xs gap-1.5">
            <IconShieldExclamation className="size-3.5 text-amber-400" /> Pending Approvals ({approvals.length})
          </TabsTrigger>
          <TabsTrigger value="findings" className="text-xs gap-1.5">
            <IconShieldCheck className="size-3.5" /> Vulnerability Findings ({findings.length})
          </TabsTrigger>
          <TabsTrigger value="patterns" className="text-xs gap-1.5">
            <IconBrain className="size-3.5" /> Test Patterns ({patterns.length})
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Pending Approvals Queue */}
        <TabsContent value="approvals" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-4 border-b border-border/40 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Human Authorization Queue (Destructive Tests)</h2>
                <p className="text-xs text-muted-foreground">
                  Destructive tests require single-use explicit approval before SandboxExecutor execution.
                </p>
              </div>
              <Badge variant="outline" className="font-mono text-[10px] border-amber-500/30 text-amber-400">
                Single-Use Policy
              </Badge>
            </div>

            {approvals.length === 0 ? (
              <div className="p-12 text-center text-xs text-muted-foreground font-mono">
                No destructive security tests currently awaiting human approval.
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {approvals.map((approval) => (
                  <div key={approval.id} className="p-5 hover:bg-muted/10 transition-colors space-y-3">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <Badge
                            variant="outline"
                            className={`text-[9px] px-1.5 py-0 ${
                              approval.method === "GET"
                                ? "text-blue-400 border-blue-500/30"
                                : approval.method === "POST"
                                ? "text-emerald-400 border-emerald-500/30"
                                : "text-amber-400 border-amber-500/30"
                            }`}
                          >
                            {approval.method}
                          </Badge>
                          <span className="font-bold text-foreground">{approval.endpoint_route}</span>
                          <span className="text-muted-foreground">&bull; Domain: {approval.target_domain || "target"}</span>
                        </div>
                        <div className="text-xs text-muted-foreground italic bg-muted/30 p-2.5 rounded-xl border border-border/40 font-sans">
                          <strong>LLM Reasoning:</strong> "{approval.reasoning_trace || "Destructive test proposal generated by Security Reasoner."}"
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReject(approval.id)}
                          className="text-xs h-8 text-muted-foreground hover:text-foreground"
                        >
                          <IconX className="size-3.5 mr-1" /> Dismiss
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApprove(approval.id)}
                          disabled={approvingId === approval.id}
                          className="text-xs h-8 bg-amber-500 hover:bg-amber-600 text-black font-semibold shadow-xs"
                        >
                          <IconCheck className="size-3.5 mr-1" />
                          {approvingId === approval.id ? "Authorizing..." : "Approve Single Run"}
                        </Button>
                      </div>
                    </div>

                    {/* Test Strategy Snapshot */}
                    <div className="bg-muted/40 p-3 rounded-xl border border-border/40 text-[11px] font-mono overflow-x-auto text-muted-foreground">
                      <pre>{JSON.stringify(approval.test_strategy_snapshot, null, 2)}</pre>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: Vulnerability Findings */}
        <TabsContent value="findings" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-4 border-b border-border/40">
              <h2 className="text-sm font-semibold text-foreground">Discovered Security Findings</h2>
              <p className="text-xs text-muted-foreground">
                Confirmed API vulnerabilities identified during autonomous crawl runs.
              </p>
            </div>

            {findings.length === 0 ? (
              <div className="p-12 text-center text-xs text-muted-foreground font-mono">
                No security vulnerabilities discovered yet. Run crawls on verified domains with active testing enabled.
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {findings.map((f) => (
                  <div key={f.id} className="p-4 hover:bg-muted/10 transition-colors flex items-center justify-between gap-4 flex-wrap">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 font-mono text-xs">
                        <Badge
                          className={`text-[9px] uppercase font-bold px-1.5 py-0 ${
                            f.severity === "critical"
                              ? "bg-rose-500 text-white"
                              : f.severity === "high"
                              ? "bg-amber-500 text-black"
                              : "bg-blue-500 text-white"
                          }`}
                        >
                          {f.severity}
                        </Badge>
                        <Badge variant="outline" className="text-[10px] uppercase font-mono px-1 py-0">
                          {f.vuln_class}
                        </Badge>
                        <span className="font-bold text-foreground">{f.method} {f.endpoint_route}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        Crawl ID: {f.crawl_id} &bull; Discovered: {new Date(f.created_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {f.ran_via_cache && (
                        <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-400 bg-emerald-500/10 gap-1 px-1.5">
                          <IconBolt className="size-3 text-emerald-400" /> Memory Replay (0 Tokens)
                        </Badge>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedFinding(f)}
                        className="text-xs h-7 gap-1"
                      >
                        <IconFileCode className="size-3.5" /> View Evidence
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 3: Security Test Patterns */}
        <TabsContent value="patterns" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-4 border-b border-border/40">
              <h2 className="text-sm font-semibold text-foreground">Adaptive Security Knowledge Graph</h2>
              <p className="text-xs text-muted-foreground">
                Domain-agnostic pattern signatures, promotion thresholds (20 occurrences + 15 distinct domains) & cache status.
              </p>
            </div>

            {patterns.length === 0 ? (
              <div className="p-12 text-center text-xs text-muted-foreground font-mono">
                No security patterns observed yet.
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {patterns.map((p) => {
                  const occProgress = Math.min(100, Math.round((p.occurrences / 20) * 100));
                  const targetProgress = Math.min(100, Math.round((p.distinct_target_count / 15) * 100));
                  return (
                    <div key={p.id} className="p-4 hover:bg-muted/10 transition-colors space-y-2.5">
                      <div className="flex items-center justify-between gap-4 flex-wrap">
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <Badge
                            variant="outline"
                            className={`text-[10px] uppercase ${
                              p.status === "learned"
                                ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10 font-bold"
                                : "border-muted text-muted-foreground"
                            }`}
                          >
                            {p.status.toUpperCase()}
                          </Badge>
                          <Badge variant="outline" className="text-[10px] uppercase font-mono">
                            {p.vuln_class}
                          </Badge>
                          <code className="text-xs text-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                            {p.endpoint_signature.slice(0, 16)}…
                          </code>
                          {p.is_destructive && (
                            <Badge className="bg-rose-500/20 text-rose-400 text-[9px] px-1 py-0">
                              Destructive (Never Promoted)
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
                          <span>Confidence: <strong className="text-foreground">{Math.round(p.confidence * 100)}%</strong></span>
                        </div>
                      </div>

                      {/* Promotion Progress Gauges */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px] font-mono">
                        <div className="space-y-1">
                          <div className="flex justify-between text-muted-foreground">
                            <span>Observations: {p.occurrences}/20</span>
                            <span>{occProgress}%</span>
                          </div>
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-primary transition-all duration-300" style={{ width: `${occProgress}%` }} />
                          </div>
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between text-muted-foreground">
                            <span>Distinct Targets: {p.distinct_target_count}/15 domains</span>
                            <span>{targetProgress}%</span>
                          </div>
                          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500 transition-all duration-300" style={{ width: `${targetProgress}%` }} />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Finding Evidence Modal */}
      <Dialog open={!!selectedFinding} onOpenChange={() => setSelectedFinding(null)}>
        <DialogContent className="max-w-2xl p-6 rounded-2xl bg-card text-card-foreground border border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <IconFileCode className="size-5 text-primary" />
              Security Finding Evidence Details
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground font-mono">
              {selectedFinding?.method} {selectedFinding?.endpoint_route} &bull; Class: {selectedFinding?.vuln_class}
            </DialogDescription>
          </DialogHeader>

          <pre className="p-4 rounded-xl bg-muted/40 border border-border/40 text-xs font-mono overflow-x-auto text-foreground max-h-[400px]">
            {JSON.stringify(selectedFinding?.evidence, null, 2)}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
