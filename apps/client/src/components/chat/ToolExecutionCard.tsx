"use client";

import React, { useState, memo } from "react";
import { cn } from "@/lib/utils";
import type { ToolCallEvent } from "@/lib/api-client/types";
import {
  ActivityIcon,
  CheckCircle2Icon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  CheckIcon,
  GlobeIcon,
  TerminalIcon,
  ShieldCheckIcon,
  FileCode2Icon,
  ClockIcon,
  SparklesIcon,
} from "lucide-react";

interface ToolExecutionCardProps {
  toolCall: ToolCallEvent;
  className?: string;
}

export const ToolExecutionCard = memo(({ toolCall, className }: ToolExecutionCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const isRunning = toolCall.status === "running";
  const isFailed = toolCall.status === "failed";
  const isSuccess = toolCall.status === "completed";

  // Pick appropriate icon based on tool
  const getToolIcon = () => {
    switch (toolCall.tool) {
      case "probe_http_endpoint":
        return <GlobeIcon className="size-3.5" />;
      case "execute_curl":
        return <TerminalIcon className="size-3.5" />;
      case "security_audit_endpoint":
        return <ShieldCheckIcon className="size-3.5" />;
      case "infer_openapi_schema":
        return <FileCode2Icon className="size-3.5" />;
      default:
        return <ActivityIcon className="size-3.5" />;
    }
  };

  // Get status badge details
  const getStatusBadge = () => {
    if (isRunning) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-[11px] font-mono text-amber-500 font-medium animate-pulse">
          <span className="size-1.5 rounded-full bg-amber-500 animate-ping" />
          Running
        </span>
      );
    }
    if (isFailed) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-[11px] font-mono text-rose-500 font-medium">
          <XCircleIcon className="size-3" />
          Failed
        </span>
      );
    }
    // Completed
    const statusCode = toolCall.output?.status_code as number | undefined;
    const latency = toolCall.latency_ms ?? (toolCall.output?.latency_ms as number | undefined);

    return (
      <div className="flex items-center gap-1.5">
        {statusCode && (
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium border",
              statusCode >= 200 && statusCode < 300
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"
                : statusCode >= 400
                ? "bg-rose-500/10 border-rose-500/20 text-rose-500"
                : "bg-blue-500/10 border-blue-500/20 text-blue-500"
            )}
          >
            <CheckCircle2Icon className="size-3" />
            {statusCode}
          </span>
        )}
        {latency !== undefined && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-muted/60 text-[10px] font-mono text-muted-foreground">
            <ClockIcon className="size-2.5" />
            {latency}ms
          </span>
        )}
      </div>
    );
  };

  const handleCopyOutput = (e: React.MouseEvent) => {
    e.stopPropagation();
    const textToCopy = JSON.stringify(toolCall.output || toolCall.input || {}, null, 2);
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const title = toolCall.title || toolCall.tool.replace(/_/g, " ");

  return (
    <div
      className={cn(
        "w-full my-2 rounded-xl border border-border/60 bg-muted/30 hover:bg-muted/40 transition-all text-xs font-sans shadow-2xs overflow-hidden",
        isRunning && "border-amber-500/30 bg-amber-500/[0.02]",
        className
      )}
    >
      {/* Header bar */}
      <div
        onClick={() => !isRunning && setIsExpanded(!isExpanded)}
        className={cn(
          "flex items-center justify-between gap-2 px-3 py-2 select-none",
          !isRunning && "cursor-pointer hover:bg-muted/50"
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Action icon badge */}
          <div
            className={cn(
              "size-6 rounded-lg flex items-center justify-center shrink-0 border",
              isRunning
                ? "bg-amber-500/10 border-amber-500/30 text-amber-500"
                : isFailed
                ? "bg-rose-500/10 border-rose-500/30 text-rose-500"
                : "bg-primary/10 border-primary/20 text-primary"
            )}
          >
            {isRunning ? (
              <span className="size-3 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
            ) : (
              getToolIcon()
            )}
          </div>

          {/* Action title */}
          <span className="font-medium text-foreground/90 truncate capitalize">
            {title}
          </span>
        </div>

        {/* Status + Expand trigger */}
        <div className="flex items-center gap-2 shrink-0">
          {getStatusBadge()}

          {!isRunning && (
            <button
              type="button"
              className="p-1 rounded text-muted-foreground hover:text-foreground"
              aria-label={isExpanded ? "Collapse tool details" : "Expand tool details"}
            >
              {isExpanded ? (
                <ChevronUpIcon className="size-3.5" />
              ) : (
                <ChevronDownIcon className="size-3.5" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expandable Inspector Body */}
      {isExpanded && !isRunning && (
        <div className="border-t border-border/50 bg-background/60 p-3 space-y-2 text-[11px] font-mono">
          {/* Input details */}
          {toolCall.input && Object.keys(toolCall.input).length > 0 && (
            <div>
              <span className="text-muted-foreground block mb-1 font-sans font-medium text-[10px] uppercase tracking-wider">
                Parameters
              </span>
              <pre className="p-2 rounded-lg bg-muted/60 text-foreground/90 overflow-x-auto text-[11px] leading-relaxed">
                {JSON.stringify(toolCall.input, null, 2)}
              </pre>
            </div>
          )}

          {/* Error display */}
          {toolCall.error && (
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
              {toolCall.error}
            </div>
          )}

          {/* Output / Response Body */}
          {toolCall.output && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-muted-foreground font-sans font-medium text-[10px] uppercase tracking-wider">
                  Live Response Telemetry
                </span>
                <button
                  type="button"
                  onClick={handleCopyOutput}
                  className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground font-sans cursor-pointer"
                >
                  {copied ? (
                    <>
                      <CheckIcon className="size-3 text-emerald-500" />
                      <span className="text-emerald-500">Copied</span>
                    </>
                  ) : (
                    <>
                      <CopyIcon className="size-3" />
                      <span>Copy Output</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-2 rounded-lg bg-muted/80 text-foreground/90 overflow-x-auto max-h-56 text-[11px] leading-relaxed">
                {JSON.stringify(toolCall.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

ToolExecutionCard.displayName = "ToolExecutionCard";
