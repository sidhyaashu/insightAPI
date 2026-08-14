"use client";

import React, { useEffect, useState, useId, memo } from "react";
import { useTheme } from "next-themes";
import { CheckIcon, CopyIcon, Code2Icon, EyeIcon, WorkflowIcon, AlertCircleIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MermaidProps } from "./types";

export const MarkdownMermaid = memo(({ chart, className }: MermaidProps) => {
  const uniqueId = useId().replace(/:/g, "_");
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"diagram" | "source">("diagram");
  const [copied, setCopied] = useState(false);

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

        const id = `mermaid_${uniqueId}_${Date.now()}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart.trim());
        if (isMounted) {
          setSvg(renderedSvg);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (isMounted) {
          console.warn("Failed to render Mermaid diagram:", err);
          setError(err instanceof Error ? err.message : "Diagram rendering failed");
          setLoading(false);
          setActiveTab("source"); // Fall back to showing source
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, isDark, uniqueId]);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "my-4 rounded-xl border border-border/70 overflow-hidden bg-card/60 shadow-xs transition-all",
        className
      )}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-muted/40 border-b border-border/50 text-xs select-none">
        <div className="flex items-center gap-2">
          <WorkflowIcon className="size-4 text-primary" />
          <span className="font-semibold text-foreground">Diagram</span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Toggle Tab */}
          <div className="flex items-center rounded-lg bg-muted/60 p-0.5 border border-border/40 text-[11px]">
            <button
              type="button"
              onClick={() => setActiveTab("diagram")}
              disabled={!!error}
              className={cn(
                "flex items-center gap-1 px-2 py-0.5 rounded-md transition-colors cursor-pointer",
                activeTab === "diagram" && !error
                  ? "bg-card text-foreground font-medium shadow-xs"
                  : "text-muted-foreground hover:text-foreground disabled:opacity-40"
              )}
            >
              <EyeIcon className="size-3" />
              <span>Preview</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("source")}
              className={cn(
                "flex items-center gap-1 px-2 py-0.5 rounded-md transition-colors cursor-pointer",
                activeTab === "source"
                  ? "bg-card text-foreground font-medium shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Code2Icon className="size-3" />
              <span>Source</span>
            </button>
          </div>

          {/* Copy source button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 rounded-md hover:bg-muted/80 transition-colors cursor-pointer"
            title="Copy Mermaid source"
          >
            {copied ? (
              <>
                <CheckIcon className="size-3 text-emerald-500" />
                <span className="text-emerald-500 font-medium">Copied</span>
              </>
            ) : (
              <>
                <CopyIcon className="size-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main preview or source body */}
      <div className="p-4">
        {activeTab === "diagram" && !error && (
          <div className="flex flex-col items-center justify-center overflow-x-auto min-h-[140px]">
            {loading ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono animate-pulse">
                <WorkflowIcon className="size-4 animate-spin" /> Rendering diagram...
              </div>
            ) : svg ? (
              <div
                className="w-full flex justify-center [&>svg]:max-w-full [&>svg]:h-auto"
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            ) : null}
          </div>
        )}

        {(activeTab === "source" || error) && (
          <div className="space-y-2">
            {error && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-destructive/10 text-destructive text-xs border border-destructive/20">
                <AlertCircleIcon className="size-4 shrink-0" />
                <span>Could not render diagram visually: {error}</span>
              </div>
            )}
            <div className="p-3 rounded-lg bg-[#111318] text-slate-200 font-mono text-xs overflow-x-auto">
              <pre className="m-0 whitespace-pre leading-relaxed">{chart}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

MarkdownMermaid.displayName = "MarkdownMermaid";
