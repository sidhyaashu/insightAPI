"use client";

import React, { useState, useEffect, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  BrainIcon,
  CheckCircle2Icon,
  Loader2Icon,
} from "lucide-react";

interface ReasoningBlockProps {
  reasoning: string;
  isStreaming?: boolean;
  durationSeconds?: number;
}

/**
 * Modern dynamic Chain-of-Thought / reasoning step component matching ChatGPT & Claude.
 * Displays animated live steps while thinking, and collapses into a sleek disclosure once completed.
 */
export function ReasoningBlock({
  reasoning,
  isStreaming = false,
  durationSeconds,
}: ReasoningBlockProps) {
  const [isOpen, setIsOpen] = useState(isStreaming);
  const [elapsed, setElapsed] = useState(durationSeconds || 0);

  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isStreaming]);

  // Keep open while streaming, let user close if desired
  useEffect(() => {
    if (isStreaming) {
      setIsOpen(true);
    }
  }, [isStreaming]);

  // Parse reasoning text into discrete step items
  const steps = useMemo(() => {
    if (!reasoning) return [];
    const lines = reasoning
      .split(/\n+/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    return lines.map((line, idx) => {
      const cleaned = line.replace(/^(\d+[\.\)]|\-|\*)\s*/, "");
      const isLast = idx === lines.length - 1;
      return {
        id: `step-${idx}`,
        label: cleaned,
        status: isStreaming && isLast ? ("active" as const) : ("complete" as const),
      };
    });
  }, [reasoning, isStreaming]);

  if (!reasoning && !isStreaming) return null;

  return (
    <div className="w-full my-2.5 rounded-2xl border border-border/50 bg-muted/20 overflow-hidden transition-all text-xs font-sans">
      {/* Header Toggle Bar */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 bg-muted/30 hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-2 font-medium">
          {isStreaming ? (
            <SparklesIcon className="size-3.5 text-primary animate-spin" />
          ) : (
            <BrainIcon className="size-3.5 text-primary/80" />
          )}

          <span className="text-xs">
            {isStreaming ? (
              <span className="inline-flex items-center gap-1.5 text-primary font-medium">
                Thinking &amp; analyzing...
                <span className="text-muted-foreground font-normal font-mono text-[11px]">
                  ({elapsed}s)
                </span>
              </span>
            ) : (
              <span>Thought for {elapsed > 0 ? `${elapsed}s` : "a moment"}</span>
            )}
          </span>
        </div>

        <div className="flex items-center gap-1 text-muted-foreground/70">
          {isOpen ? (
            <ChevronDownIcon className="size-3.5 transition-transform" />
          ) : (
            <ChevronRightIcon className="size-3.5 transition-transform" />
          )}
        </div>
      </button>

      {/* Expandable Step Details */}
      {isOpen && (
        <div className="px-4 py-3 bg-background/50 border-t border-border/30 text-xs text-muted-foreground leading-relaxed font-sans overflow-x-auto max-h-72 overflow-y-auto">
          {steps.length > 0 ? (
            <div className="space-y-2.5">
              {steps.map((step) => (
                <div key={step.id} className="flex items-start gap-2.5 text-xs">
                  <div className="mt-0.5 shrink-0">
                    {step.status === "active" ? (
                      <Loader2Icon className="size-3.5 text-primary animate-spin" />
                    ) : (
                      <CheckCircle2Icon className="size-3.5 text-emerald-500" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "flex-1 leading-snug",
                      step.status === "active"
                        ? "text-foreground font-medium"
                        : "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2.5 text-xs italic text-muted-foreground/80 py-1">
              <span className="size-2 rounded-full bg-primary animate-ping" />
              <span>Analyzing API requirements &amp; formulating execution plan...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
