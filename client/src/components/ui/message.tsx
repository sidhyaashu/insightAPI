"use client";

import React, { useState, useMemo, memo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  CheckIcon,
  CopyIcon,
  SparklesIcon,
  UserIcon,
  RotateCwIcon,
  TerminalIcon,
  FileCodeIcon,
} from "lucide-react";
import type { ComponentProps, HTMLAttributes } from "react";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const Message = ({ className, from, children, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full gap-3 py-2 transition-all",
      from === "user" ? "justify-end" : "justify-start",
      className
    )}
    {...props}
  >
    {from === "assistant" && (
      <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent text-primary border border-primary/30 mt-0.5 shadow-xs">
        <SparklesIcon className="size-4" />
      </div>
    )}

    <div
      className={cn(
        "flex max-w-[88%] sm:max-w-[80%] flex-col gap-1.5 min-w-0",
        from === "user" ? "items-end" : "items-start"
      )}
    >
      {children}
    </div>

    {from === "user" && (
      <div className="flex size-8 shrink-0 items-center justify-center rounded-xl bg-muted border border-border/70 text-foreground mt-0.5 shadow-xs font-semibold text-xs">
        <UserIcon className="size-4 text-muted-foreground" />
      </div>
    )}
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
      "flex flex-col gap-2 rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs transition-colors",
      from === "user"
        ? "bg-muted/80 text-foreground border border-border/70 rounded-tr-xs"
        : "bg-card text-card-foreground border border-border/70 rounded-tl-xs",
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

/** Code block renderer with syntax styling and copy button */
const CodeBlock = ({ language, code }: { language: string; code: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-border/70 bg-[#0d1117] text-slate-100 shadow-md font-mono text-xs max-w-full">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#161b22] border-b border-border/40 text-[11px] text-muted-foreground select-none">
        <span className="font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <FileCodeIcon className="size-3.5 text-primary" />
          {language || "code"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer px-2 py-0.5 rounded hover:bg-slate-800"
        >
          {copied ? (
            <>
              <CheckIcon className="size-3 text-emerald-400" />
              <span className="text-emerald-400 font-sans">Copied!</span>
            </>
          ) : (
            <>
              <CopyIcon className="size-3" />
              <span className="font-sans">Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3.5 overflow-x-auto no-scrollbar leading-relaxed">
        <pre className="m-0 font-mono whitespace-pre">{code}</pre>
      </div>
    </div>
  );
};

/** Enhanced Markdown renderer for streaming token responses */
export const MessageResponse = memo(({ content, isStreaming, onRegenerate }: MessageResponseProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopyMessage = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Parse markdown code blocks and paragraphs
  const renderedContent = useMemo(() => {
    if (!content) return null;

    const parts = [];
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // Text before code block
      if (match.index > lastIndex) {
        parts.push({
          type: "text",
          value: content.substring(lastIndex, match.index),
        });
      }
      // Code block
      parts.push({
        type: "code",
        language: match[1] || "text",
        value: match[2].trimEnd(),
      });
      lastIndex = match.index + match[0].length;
    }

    // Trailing text or partial streaming code block
    if (lastIndex < content.length) {
      const remaining = content.substring(lastIndex);
      // Check if we are in an unclosed streaming code block
      if (isStreaming && remaining.includes("```")) {
        const streamParts = remaining.split("```");
        if (streamParts[0]) {
          parts.push({ type: "text", value: streamParts[0] });
        }
        const codeLines = streamParts[1] || "";
        const firstLineEnd = codeLines.indexOf("\n");
        const lang = firstLineEnd !== -1 ? codeLines.substring(0, firstLineEnd) : "";
        const codeVal = firstLineEnd !== -1 ? codeLines.substring(firstLineEnd + 1) : codeLines;
        parts.push({ type: "code", language: lang || "code", value: codeVal });
      } else {
        parts.push({ type: "text", value: remaining });
      }
    }

    return parts;
  }, [content, isStreaming]);

  return (
    <div className="relative group/msg w-full space-y-2 font-sans">
      <div className="text-xs sm:text-sm text-foreground leading-relaxed break-words">
        {renderedContent?.map((part, idx) => {
          if (part.type === "code") {
            return <CodeBlock key={idx} language={part.language || "text"} code={part.value || ""} />;
          }

          // Format line breaks, bold, inline code in text segments
          return (
            <div key={idx} className="whitespace-pre-wrap space-y-2">
              {part.value}
            </div>
          );
        })}

        {isStreaming && (
          <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle rounded-xs" />
        )}
      </div>

      {/* Message action buttons */}
      {!isStreaming && content && (
        <div className="opacity-0 group-hover/msg:opacity-100 transition-opacity flex items-center gap-2 pt-2 border-t border-border/30">
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
});
