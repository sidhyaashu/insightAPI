"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  IconArrowLeft,
  IconDownload,
  IconCode,
  IconCopy,
  IconCheck,
  IconPlayerPlay,
  IconGitCompare,
  IconFileText,
  IconBraces,
  IconBrandPython,
  IconBrandTypescript,
  IconFileZip,
  IconRefresh,
  IconWorld,
  IconSparkles,
  IconRoute,
  IconActivity,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import type { CrawlSession, CrawlReport } from "@/lib/api-client/types";
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

export default function CrawlReportDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.id as string;

  const [session, setSession] = useState<CrawlSession | null>(null);
  const [report, setReport] = useState<CrawlReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Test Suite Generator Modal State
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testFormat, setTestFormat] = useState<"python" | "typescript">("python");
  const [generatedCode, setGeneratedCode] = useState<string>("");
  const [loadingTestCode, setLoadingTestCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);

  const loadData = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const [sessionData, reportData] = await Promise.allSettled([
        crawlsApi.getCrawlById(sessionId),
        crawlsApi.getReport(sessionId),
      ]);

      if (sessionData.status === "fulfilled") {
        setSession(sessionData.value);
      }
      if (reportData.status === "fulfilled") {
        setReport(reportData.value);
      }
    } catch (err: unknown) {
      setError("Failed to load crawl report details.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load generated test code when modal opens or format changes
  const fetchTestCode = useCallback(async (fmt: "python" | "typescript") => {
    setLoadingTestCode(true);
    try {
      const code = await crawlsApi.generateTests(sessionId, fmt);
      setGeneratedCode(code);
    } catch (err) {
      toast.error("Failed to generate test script.");
      setGeneratedCode("# Failed to generate Playwright test script.");
    } finally {
      setLoadingTestCode(false);
    }
  }, [sessionId]);

  const handleOpenTestModal = () => {
    setTestModalOpen(true);
    fetchTestCode(testFormat);
  };

  const handleFormatChange = (fmt: "python" | "typescript") => {
    setTestFormat(fmt);
    fetchTestCode(fmt);
  };

  const handleCopyCode = () => {
    if (!generatedCode) return;
    navigator.clipboard.writeText(generatedCode);
    setCopied(true);
    toast.success("Test script copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadScript = () => {
    const filename =
      testFormat === "typescript"
        ? `test_regression_${sessionId}.spec.ts`
        : `test_regression_${sessionId}.py`;
    const mime = testFormat === "typescript" ? "text/typescript" : "text/x-python";
    handleDownloadFile(generatedCode, filename, mime);
    toast.success(`Downloaded ${filename}`);
  };

  const handleDownloadZip = async () => {
    setDownloadingZip(true);
    try {
      const blob = await crawlsApi.downloadTestSuiteZip(sessionId, testFormat);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `insightapi_test_suite_${sessionId}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Downloaded full CI/CD test suite package!");
    } catch (err) {
      toast.error("Failed to download zip package.");
    } finally {
      setDownloadingZip(false);
    }
  };

  const actionTraces = session?.action_traces || report?.action_traces || [];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-muted-foreground min-h-[60vh]">
        <div className="size-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <span className="text-sm font-mono">Loading report details…</span>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto w-full font-sans pb-28">
      {/* Top Navigation & Actions Bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <Link href="/reports">
            <Button variant="ghost" size="sm" className="gap-1 text-xs">
              <IconArrowLeft className="size-4" /> Back to Reports
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-foreground truncate max-w-md">
                {session?.target_url || "Crawl Report"}
              </h1>
              <Badge variant="outline" className="text-[10px] font-mono border-primary/30 text-primary bg-primary/5">
                {session?.status?.toUpperCase() || "COMPLETED"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">Session: {sessionId}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            onClick={handleOpenTestModal}
            className="gap-1.5 text-xs bg-primary text-primary-foreground font-semibold shadow-xs"
          >
            <IconPlayerPlay className="size-3.5" />
            Generate Test Suite
          </Button>

          {report?.openapi_spec && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                handleDownloadFile(
                  JSON.stringify(report.openapi_spec, null, 2),
                  `openapi_${sessionId}.json`,
                  "application/json"
                )
              }
              className="gap-1.5 text-xs"
            >
              <IconBraces className="size-3.5" />
              OpenAPI JSON
            </Button>
          )}

          {report?.postman_collection && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                handleDownloadFile(
                  JSON.stringify(report.postman_collection, null, 2),
                  `postman_${sessionId}.json`,
                  "application/json"
                )
              }
              className="gap-1.5 text-xs"
            >
              <IconCode className="size-3.5" />
              Postman JSON
            </Button>
          )}

          {report?.markdown_docs && (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                handleDownloadFile(report.markdown_docs!, `docs_${sessionId}.md`, "text/markdown")
              }
              className="gap-1.5 text-xs"
            >
              <IconFileText className="size-3.5" />
              Markdown
            </Button>
          )}

          <Link href={`/reports/${sessionId}/drift`}>
            <Button variant="outline" size="sm" className="gap-1.5 text-xs border-primary/30 text-primary">
              <IconGitCompare className="size-3.5" />
              Drift Diff
            </Button>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Captured Endpoints</div>
          <div className="text-2xl font-bold font-mono text-foreground">{session?.captured_count || 0}</div>
        </div>
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Recorded Action Steps</div>
          <div className="text-2xl font-bold font-mono text-primary">{actionTraces.length}</div>
        </div>
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Max Pages Explored</div>
          <div className="text-2xl font-bold font-mono text-foreground">{session?.max_pages || 10}</div>
        </div>
        <div className="p-4 rounded-xl border border-border/60 bg-card shadow-xs">
          <div className="text-xs text-muted-foreground font-mono mb-1">Goal Alignment</div>
          <div className="text-xs font-semibold text-foreground truncate mt-1.5" title={session?.goal || "All APIs"}>
            {session?.goal || "Explore all APIs"}
          </div>
        </div>
      </div>

      {/* Main Tabs Section */}
      <Tabs defaultValue="actions" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-md">
          <TabsTrigger value="actions" className="text-xs gap-1.5">
            <IconRoute className="size-3.5" /> Replayable Flow ({actionTraces.length})
          </TabsTrigger>
          <TabsTrigger value="openapi" className="text-xs gap-1.5">
            <IconBraces className="size-3.5" /> OpenAPI Spec
          </TabsTrigger>
          <TabsTrigger value="markdown" className="text-xs gap-1.5">
            <IconFileText className="size-3.5" /> Markdown Docs
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Replayable Actions Timeline */}
        <TabsContent value="actions" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-4 border-b border-border/40 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <IconActivity className="size-4 text-primary" /> Recorded Crawl Action Traces
              </h2>
              <Button size="sm" variant="outline" onClick={handleOpenTestModal} className="text-xs gap-1">
                <IconCode className="size-3.5 text-primary" /> Convert to Test Suite
              </Button>
            </div>

            {actionTraces.length === 0 ? (
              <div className="p-10 text-center text-xs text-muted-foreground font-mono">
                No interactive actions recorded during this crawl run.
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {actionTraces.map((trace: any, i: number) => {
                  const calls = trace.network_calls_triggered || [];
                  return (
                    <div key={i} className="p-4 hover:bg-muted/10 transition-colors space-y-2">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-2 font-mono text-xs flex-wrap">
                          <span className="size-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">
                            {trace.step || i + 1}
                          </span>
                          <Badge variant="outline" className="text-[10px] uppercase font-mono px-1.5 py-0">
                            {trace.action_type || "click"}
                          </Badge>
                          <code className="text-xs text-foreground bg-muted/40 px-1.5 py-0.5 rounded">
                            {trace.selector || "window"}
                          </code>
                          {trace.value && (
                            <span className="text-muted-foreground text-[11px]">
                              value: <strong className="text-foreground">"{trace.value}"</strong>
                            </span>
                          )}
                          {trace.is_vision_action && (
                            <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/30 text-[9px] px-1.5 py-0">
                              👁️ Vision LLM Coordinate
                            </Badge>
                          )}
                          {trace.humanized && (
                            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/30 text-[9px] px-1.5 py-0">
                              ✦ Humanized Bezier Movement
                            </Badge>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {calls.length} API {calls.length === 1 ? "call" : "calls"} triggered
                        </span>
                      </div>

                      {/* Form Submission Attribution Card */}
                      {(trace.action_type === "form_submit" || trace.form_action || trace.submitted_fields) && (
                        <div className="bg-muted/30 p-2.5 rounded-xl border border-border/50 text-[11px] font-mono space-y-1 mt-1">
                          <div className="flex items-center gap-2 text-primary font-bold text-[10px] uppercase">
                            <span>Form Submission Context</span>
                            {trace.form_method && (
                              <Badge variant="outline" className="text-[9px] px-1 py-0 border-primary/30">
                                {trace.form_method} {trace.form_action}
                              </Badge>
                            )}
                          </div>
                          {trace.submitted_fields && (
                            <div className="text-muted-foreground text-[10px] truncate">
                              Fields: {JSON.stringify(trace.submitted_fields)}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Triggered Network Calls */}
                      {calls.length > 0 && (
                        <div className="pl-7 space-y-1.5 pt-1">
                          {calls.map((call: any, cIdx: number) => (
                            <div
                              key={cIdx}
                              className="flex items-center gap-2 text-[11px] font-mono bg-muted/30 p-1.5 rounded-lg border border-border/40"
                            >
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1 py-0 ${
                                  call.method === "GET"
                                    ? "text-blue-400 border-blue-500/30"
                                    : call.method === "POST"
                                    ? "text-emerald-400 border-emerald-500/30"
                                    : "text-amber-400 border-amber-500/30"
                                }`}
                              >
                                {call.method}
                              </Badge>
                              <span className="text-foreground truncate flex-1">{call.url || call.template_route}</span>
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1 py-0 ${
                                  (call.status || 200) < 400
                                    ? "text-emerald-500 border-emerald-500/30"
                                    : "text-destructive border-destructive/30"
                                }`}
                              >
                                {call.status || 200}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: OpenAPI Spec */}
        <TabsContent value="openapi" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-3 border-b border-border/40 flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground">OpenAPI 3.0.3 Document</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(report?.openapi_spec, null, 2));
                  toast.success("OpenAPI JSON copied!");
                }}
                className="text-xs gap-1"
              >
                <IconCopy className="size-3.5" /> Copy JSON
              </Button>
            </div>
            <pre className="p-4 text-xs font-mono overflow-x-auto text-foreground max-h-[600px]">
              {report?.openapi_spec ? JSON.stringify(report.openapi_spec, null, 2) : "No spec available"}
            </pre>
          </div>
        </TabsContent>

        {/* Tab 3: Markdown Docs */}
        <TabsContent value="markdown" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
            <div className="p-3 border-b border-border/40 flex items-center justify-between">
              <span className="text-xs font-mono text-muted-foreground">API Reference Document</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(report?.markdown_docs || "");
                  toast.success("Markdown docs copied!");
                }}
                className="text-xs gap-1"
              >
                <IconCopy className="size-3.5" /> Copy Markdown
              </Button>
            </div>
            <pre className="p-4 text-xs font-mono whitespace-pre-wrap overflow-x-auto text-foreground max-h-[600px]">
              {report?.markdown_docs || "No markdown docs generated"}
            </pre>
          </div>
        </TabsContent>

        {/* Tab 4: LLM Cost & Tokens */}
        <TabsContent value="costs" className="mt-4">
          <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden p-6 space-y-4 font-mono text-xs">
            <h2 className="text-sm font-semibold text-foreground font-sans">LLM Cost & Token Ledger</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-3 rounded-xl bg-muted/30 border border-border/40">
                <div className="text-[10px] text-muted-foreground">Total AI Spend</div>
                <div className="text-lg font-bold text-amber-500">${(session?.cost_usd || 0).toFixed(4)}</div>
              </div>
              <div className="p-3 rounded-xl bg-muted/30 border border-border/40">
                <div className="text-[10px] text-muted-foreground">Tokens Consumed</div>
                <div className="text-lg font-bold text-foreground">{(session?.total_tokens || 0).toLocaleString()}</div>
              </div>
              <div className="p-3 rounded-xl bg-muted/30 border border-border/40">
                <div className="text-[10px] text-muted-foreground">Prompt / Completion Ratio</div>
                <div className="text-lg font-bold text-primary">
                  {session?.prompt_tokens || 0} / {session?.completion_tokens || 0}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Playwright Test Generator Modal */}
      <Dialog open={testModalOpen} onOpenChange={setTestModalOpen}>
        <DialogContent className="max-w-3xl p-6 rounded-2xl bg-card text-card-foreground border border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <IconPlayerPlay className="size-5 text-primary" />
              Playwright Regression Test Suite Generator
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Automated regression script replaying recorded crawl actions with network assertions and response schema validations.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Format Selector Bar */}
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 p-1 rounded-xl bg-muted/40 border border-border/60">
                <Button
                  size="sm"
                  variant={testFormat === "python" ? "default" : "ghost"}
                  onClick={() => handleFormatChange("python")}
                  className="text-xs gap-1.5 h-8 px-3"
                >
                  <IconBrandPython className="size-3.5 text-blue-400" />
                  Python (pytest-playwright)
                </Button>
                <Button
                  size="sm"
                  variant={testFormat === "typescript" ? "default" : "ghost"}
                  onClick={() => handleFormatChange("typescript")}
                  className="text-xs gap-1.5 h-8 px-3"
                >
                  <IconBrandTypescript className="size-3.5 text-cyan-400" />
                  TypeScript (@playwright/test)
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={handleCopyCode} className="text-xs gap-1.5 h-8">
                  {copied ? <IconCheck className="size-3.5 text-emerald-500" /> : <IconCopy className="size-3.5" />}
                  {copied ? "Copied!" : "Copy Code"}
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadScript} className="text-xs gap-1.5 h-8">
                  <IconDownload className="size-3.5" />
                  Download Script
                </Button>
                <Button
                  size="sm"
                  onClick={handleDownloadZip}
                  disabled={downloadingZip}
                  className="text-xs gap-1.5 h-8 bg-primary text-primary-foreground font-semibold"
                >
                  <IconFileZip className="size-3.5" />
                  {downloadingZip ? "Packaging..." : "Download Full Suite (.zip)"}
                </Button>
              </div>
            </div>

            {/* Code Preview Box */}
            <div className="border border-border/60 rounded-xl bg-muted/30 overflow-hidden">
              <div className="px-3 py-2 border-b border-border/40 bg-muted/50 flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                <span>{testFormat === "typescript" ? "tests/regression.spec.ts" : "tests/test_api_regression.py"}</span>
                <span>{actionTraces.length} recorded actions</span>
              </div>
              {loadingTestCode ? (
                <div className="p-12 text-center text-xs text-muted-foreground font-mono animate-pulse">
                  Generating Playwright regression test suite…
                </div>
              ) : (
                <pre className="p-4 text-xs font-mono overflow-x-auto text-foreground max-h-[420px] leading-relaxed">
                  {generatedCode}
                </pre>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
