"use client";

import React, { useState, useEffect, useId, memo } from "react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import {
  XIcon,
  CopyIcon,
  CheckIcon,
  MaximizeIcon,
  MinimizeIcon,
  DownloadIcon,
  Code2Icon,
  EyeIcon,
  AlertCircleIcon,
  Loader2Icon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useArtifact } from "./ArtifactContext";
import { artifactBadgeLabel } from "./artifact-utils";
import type { ArtifactType } from "./ArtifactContext";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { CodeBlock } from "@/components/markdown/MarkdownCode";

// ─── Pure SVG Mermaid Canvas for Workspace Panel (No Nested Cards) ─────────────

const PanelMermaidCanvas = memo(({ chart }: { chart: string }) => {
  const uniqueId = useId().replace(/:/g, "_");
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const renderChart = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: isDark ? "dark" : "default",
          securityLevel: "loose",
          fontFamily: "var(--font-sans), sans-serif",
          themeVariables: isDark
            ? {
                primaryColor: "#3b82f6",
                primaryTextColor: "#f8fafc",
                primaryBorderColor: "#60a5fa",
                lineColor: "#94a3b8",
                secondaryColor: "#1e293b",
                tertiaryColor: "#0f172a",
              }
            : undefined,
        });

        const id = `panel_mermaid_${uniqueId}_${Date.now()}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart.trim());
        if (isMounted) {
          setSvg(renderedSvg);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (isMounted) {
          console.warn("Failed to render Mermaid diagram in workspace panel:", err);
          setError(err instanceof Error ? err.message : "Diagram rendering failed");
          setLoading(false);
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, isDark, uniqueId]);

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 text-muted-foreground text-xs gap-3">
        <Loader2Icon className="size-5 animate-spin text-primary" />
        <span className="font-mono text-[11px]">Rendering architecture diagram...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center gap-3">
        <div className="flex items-center gap-2 p-3 rounded-xl bg-destructive/10 text-destructive text-xs border border-destructive/20 max-w-md">
          <AlertCircleIcon className="size-4 shrink-0" />
          <span>Could not render visual diagram: {error}</span>
        </div>
        <pre className="p-4 rounded-xl bg-muted/40 font-mono text-xs text-left max-w-lg overflow-auto border border-border/40">
          {chart}
        </pre>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto p-8 flex items-center justify-center bg-transparent">
      <div
        className="w-full max-w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:drop-shadow-sm"
        dangerouslySetInnerHTML={{ __html: svg || "" }}
      />
    </div>
  );
});

PanelMermaidCanvas.displayName = "PanelMermaidCanvas";

// ─── Content Renderer with Preview vs Code Tabs ────────────────────────────────

interface ContentProps {
  type: ArtifactType;
  content: string;
  language?: string;
  viewMode: "preview" | "code";
}

const ArtifactBody = memo(({ type, content, language, viewMode }: ContentProps) => {
  // Raw Code View Tab
  if (viewMode === "code") {
    const codeLang = type === "diagram" ? "mermaid" : language || "markdown";
    return (
      <div className="flex-1 overflow-auto p-4 bg-transparent">
        <CodeBlock language={codeLang} code={content} />
      </div>
    );
  }

  // Visual Preview Tab
  if (type === "diagram") {
    return <PanelMermaidCanvas chart={content} />;
  }

  if (type === "code") {
    return (
      <div className="flex-1 overflow-auto p-4 bg-transparent">
        <CodeBlock language={language || "text"} code={content} />
      </div>
    );
  }

  // Document or table markdown preview
  return (
    <div className="flex-1 overflow-auto px-6 py-5 bg-transparent">
      <MarkdownRenderer content={content} />
    </div>
  );
});

ArtifactBody.displayName = "ArtifactBody";

// ─── Workspace Panel Component (Transparent Navbar, Clean Modern Aesthetic) ──

export const ArtifactPanel = memo(() => {
  const { artifact, isPanelOpen, closePanel } = useArtifact();
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [viewMode, setViewMode] = useState<"preview" | "code">("preview");

  if (!artifact && !isPanelOpen) return null;

  const handleCopy = () => {
    if (!artifact) return;
    navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!artifact) return;
    const extMap: Record<string, string> = {
      diagram: "mmd",
      table: "md",
      document: "md",
      typescript: "ts",
      javascript: "js",
      python: "py",
      json: "json",
      yaml: "yaml",
      sql: "sql",
    };
    const ext = extMap[artifact.language || artifact.type] || "txt";
    const filename = `${artifact.title.toLowerCase().replace(/[^a-z0-9]/g, "_")}.${ext}`;

    const blob = new Blob([artifact.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const badgeLabel = artifact ? artifactBadgeLabel(artifact.type, artifact.language) : "";

  return (
    <div
      className={cn(
        // Base layout: clean border and background
        "flex flex-col h-full bg-background border-l border-border/40 transition-all duration-300 ease-in-out overflow-hidden shrink-0 z-30",
        // Width: normal (48%) vs fullscreen
        expanded
          ? "fixed inset-0 z-50 w-full border-0 rounded-none bg-background"
          : "w-[48%] max-w-[850px] min-w-[340px]",
        // Open/close transition
        isPanelOpen
          ? "opacity-100 translate-x-0"
          : "opacity-0 translate-x-12 pointer-events-none w-0 min-w-0"
      )}
      aria-label="Artifacts Workspace Panel"
    >
      {/* ── Navbar Header: Transparent & Minimal (No AI Logo) ───────────── */}
      <div className="flex items-center justify-between gap-2 px-5 py-3 border-b border-border/30 bg-transparent shrink-0 select-none">
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Title with clean typography */}
          <span className="text-sm font-semibold text-foreground tracking-tight truncate min-w-0">
            {artifact?.title ?? "Artifact"}
          </span>

          {/* Minimal Type badge */}
          {badgeLabel && (
            <Badge
              variant="secondary"
              className="text-[10px] font-mono px-1.5 py-0 h-4.5 shrink-0 bg-muted/60 border border-border/40 text-muted-foreground font-normal"
            >
              {badgeLabel}
            </Badge>
          )}
        </div>

        {/* ── Action Controls & Toggle Tabs ───────────────────────────── */}
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Preview vs Code Toggle Tabs */}
          <div className="flex items-center rounded-xl bg-muted/40 p-0.5 border border-border/30 mr-1">
            <button
              type="button"
              onClick={() => setViewMode("preview")}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg transition-all cursor-pointer",
                viewMode === "preview"
                  ? "bg-background text-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <EyeIcon className="size-3.5" />
              <span>Preview</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode("code")}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-lg transition-all cursor-pointer",
                viewMode === "code"
                  ? "bg-background text-foreground shadow-xs font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Code2Icon className="size-3.5" />
              <span>Code</span>
            </button>
          </div>

          {/* Copy */}
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 cursor-pointer"
            onClick={handleCopy}
            title="Copy content"
          >
            {copied ? (
              <CheckIcon className="size-4 text-emerald-500" />
            ) : (
              <CopyIcon className="size-4" />
            )}
          </Button>

          {/* Download */}
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 cursor-pointer"
            onClick={handleDownload}
            title="Download file"
          >
            <DownloadIcon className="size-4" />
          </Button>

          {/* Expand / minimize */}
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50 cursor-pointer"
            onClick={() => setExpanded((e) => !e)}
            title={expanded ? "Exit full screen" : "Full screen"}
          >
            {expanded ? (
              <MinimizeIcon className="size-4" />
            ) : (
              <MaximizeIcon className="size-4" />
            )}
          </Button>

          {/* Close */}
          <Button
            variant="ghost"
            size="icon"
            className="size-8 rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
            onClick={closePanel}
            title="Close panel"
          >
            <XIcon className="size-4" />
          </Button>
        </div>
      </div>

      {/* ── Body ────────────────────────────────────────────────────────── */}
      {artifact && (
        <ArtifactBody
          type={artifact.type}
          content={artifact.content}
          language={artifact.language}
          viewMode={viewMode}
        />
      )}
    </div>
  );
});

ArtifactPanel.displayName = "ArtifactPanel";
