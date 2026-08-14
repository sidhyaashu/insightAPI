"use client";

import React, { useState, memo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CheckIcon, CopyIcon, RotateCwIcon } from "lucide-react";
import type { HTMLAttributes } from "react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";

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
 * Enhanced modern AI assistant response renderer with full Markdown,
 * syntax highlighting, KaTeX math, HTTP API blocks, and diagrams.
 */
export const MessageResponse = memo(
  ({ content, isStreaming, onRegenerate }: MessageResponseProps) => {
    const [copied, setCopied] = useState(false);

    const handleCopyMessage = () => {
      navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    return (
      <div className="relative group/msg w-full space-y-2 font-sans min-w-0">
        <MarkdownRenderer content={content} isStreaming={isStreaming} />

        {/* Message action buttons */}
        {!isStreaming && content && (
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
          </div>
        )}
      </div>
    );
  }
);

MessageResponse.displayName = "MessageResponse";
