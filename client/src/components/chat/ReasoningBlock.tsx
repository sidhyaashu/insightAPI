"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { ChevronDownIcon, ChevronRightIcon, SparklesIcon, BrainIcon } from "lucide-react";

interface ReasoningBlockProps {
  reasoning: string;
  isStreaming?: boolean;
  durationSeconds?: number;
}

/**
 * Modern collapsible reasoning / thinking step component matching Claude & ChatGPT.
 * Displays an animated pulse while thinking, and collapses into a sleek disclosure once completed.
 */
export function ReasoningBlock({
  reasoning,
  isStreaming = false,
  durationSeconds,
}: ReasoningBlockProps) {
  // Open by default while streaming thoughts; collapsed by default once done
  const [isOpen, setIsOpen] = useState(isStreaming);
  const [elapsed, setElapsed] = useState(durationSeconds || 0);

  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isStreaming]);

  if (!reasoning && !isStreaming) return null;

  return (
    <div className="w-full my-2 rounded-2xl border border-border/50 bg-muted/20 overflow-hidden transition-all text-xs font-sans">
      {/* Header Toggle */}
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
              <span className="inline-flex items-center gap-1 text-primary">
                Thinking... <span className="text-muted-foreground font-normal">({elapsed}s)</span>
              </span>
            ) : (
              <span>Thought process {elapsed > 0 ? `(${elapsed}s)` : ""}</span>
            )}
          </span>
        </div>

        <div className="flex items-center gap-1 text-muted-foreground/70">
          {isOpen ? (
            <ChevronDownIcon className="size-3.5" />
          ) : (
            <ChevronRightIcon className="size-3.5" />
          )}
        </div>
      </button>

      {/* Expandable Reasoning Details */}
      {isOpen && (
        <div className="px-4 py-3 bg-background/50 border-t border-border/30 text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap font-mono font-normal overflow-x-auto max-h-72 overflow-y-auto no-scrollbar">
          {reasoning || (
            <div className="flex items-center gap-2 italic text-muted-foreground/60">
              <span className="size-2 rounded-full bg-primary animate-ping" />
              Formulating step-by-step reasoning...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
