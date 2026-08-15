"use client";

import React, { useState, useMemo, memo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  CheckIcon,
  CopyIcon,
  RotateCwIcon,
  PanelRightOpenIcon,
  SparklesIcon,
} from "lucide-react";
import type { HTMLAttributes } from "react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { useArtifact } from "@/components/chat/ArtifactContext";
import { extractArtifact } from "@/components/chat/artifact-utils";
import { ReasoningBlock } from "@/components/chat/ReasoningBlock";
import { ArtifactCard } from "@/components/chat/ArtifactCard";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const Message = ({ className, from, children, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full py-1.5 transition-all",
      from === "user" ? "justify-end" : "justify-start",
      className
    )}
    {...props}
  >
    <div
      className={cn(
        "flex flex-col min-w-0 transition-all",
        from === "user"
          ? "items-end max-w-[88%] sm:max-w-[78%]"
          : "items-start w-full max-w-full"
      )}
    >
      {children}
    </div>
  </div>
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const MessageContent = ({
  children,
  className,
  from,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      "text-sm leading-relaxed transition-colors",
      from === "user"
        ? "bg-muted/80 text-foreground border border-border/60 rounded-3xl px-4 py-2.5 shadow-xs break-words"
        : "w-full text-foreground bg-transparent border-0 px-0 sm:px-1 py-1 break-words shadow-none",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

export type MessageResponseProps = {
  content: string;
  isStreaming?: boolean;
  onRegenerate?: () => void;
};

/**
 * Enhanced modern AI assistant response renderer with reasoning steps,
 * full Markdown, syntax highlighting, KaTeX math, HTTP API blocks, and diagrams.
 */
export const MessageResponse = memo(
  ({ content, isStreaming, onRegenerate }: MessageResponseProps) => {
    const [copied, setCopied] = useState(false);
    const { openPanel } = useArtifact();

    // Parse <think>...</think> reasoning blocks if present
    const { reasoning, mainContent, isThinkingNow } = useMemo(() => {
      if (!content) {
        return { reasoning: "", mainContent: "", isThinkingNow: isStreaming };
      }

      const thinkStart = content.indexOf("<think>");
      if (thinkStart !== -1) {
        const thinkEnd = content.indexOf("</think>");
        if (thinkEnd !== -1) {
          return {
            reasoning: content.slice(thinkStart + 7, thinkEnd).trim(),
            mainContent: content.slice(thinkEnd + 8).trim(),
            isThinkingNow: false,
          };
        } else {
          // Still generating inside <think>
          return {
            reasoning: content.slice(thinkStart + 7).trim(),
            mainContent: "",
            isThinkingNow: true,
          };
        }
      }

      return { reasoning: "", mainContent: content, isThinkingNow: false };
    }, [content, isStreaming]);

    // Detect if this message contains a panel-worthy artifact
    const artifact = useMemo(() => {
      if (!mainContent || isStreaming) return null;
      return extractArtifact(mainContent);
    }, [mainContent, isStreaming]);

    const handleCopyMessage = () => {
      navigator.clipboard.writeText(mainContent || content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    const handleOpenPanel = () => {
      if (artifact) openPanel(artifact);
    };

    // If streaming and not a single token received yet
    if (isStreaming && !content) {
      return (
        <div className="flex items-center gap-2.5 text-xs text-muted-foreground/80 py-2 animate-in fade-in select-none">
          <SparklesIcon className="size-4 text-primary animate-spin" />
          <span className="font-medium animate-pulse text-foreground/90">
            Thinking &amp; analyzing...
          </span>
        </div>
      );
    }

    return (
      <div className="relative group/msg w-full space-y-2 font-sans min-w-0">
        {/* Reasoning / Thought Collapsible Box (Claude / ChatGPT style) */}
        {(reasoning || isThinkingNow) && (
          <ReasoningBlock reasoning={reasoning} isStreaming={isThinkingNow} />
        )}

        {/* Main Response Markdown */}
        {mainContent && (
          <MarkdownRenderer content={mainContent} isStreaming={isStreaming && !isThinkingNow} />
        )}

        {/* Inline Artifact Tile (Claude.ai style) */}
        {!isStreaming && artifact && (
          <ArtifactCard artifact={artifact} />
        )}

        {/* Message action buttons */}
        {!isStreaming && (mainContent || content) && (
          <div className="opacity-0 group-hover/msg:opacity-100 transition-opacity flex items-center gap-1.5 pt-2 border-t border-border/30">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground cursor-pointer flex items-center gap-1"
              onClick={handleCopyMessage}
              title="Copy full response"
            >
              {copied ? (
                <>
                  <CheckIcon className="size-3 text-emerald-500" />
                  <span className="text-emerald-500">Copied</span>
                </>
              ) : (
                <>
                  <CopyIcon className="size-3" />
                  <span>Copy</span>
                </>
              )}
            </Button>

            {onRegenerate && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground cursor-pointer flex items-center gap-1"
                onClick={onRegenerate}
                title="Regenerate response"
              >
                <RotateCwIcon className="size-3" />
                <span>Retry</span>
              </Button>
            )}

            {/* Open in Artifact Panel */}
            {artifact && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-[11px] text-muted-foreground hover:text-primary cursor-pointer flex items-center gap-1 ml-auto"
                onClick={handleOpenPanel}
                title="Open in side panel"
              >
                <PanelRightOpenIcon className="size-3" />
                <span>Open in panel</span>
              </Button>
            )}
          </div>
        )}
      </div>
    );
  }
);

MessageResponse.displayName = "MessageResponse";
