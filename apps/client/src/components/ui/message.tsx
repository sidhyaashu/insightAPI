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
  GlobeIcon,
  ThumbsUpIcon,
  ThumbsDownIcon,
} from "lucide-react";
import type { HTMLAttributes } from "react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import { useArtifact } from "@/components/chat/ArtifactContext";
import { extractArtifact } from "@/components/chat/artifact-utils";
import { ReasoningBlock } from "@/components/chat/ReasoningBlock";
import { ArtifactCard } from "@/components/chat/ArtifactCard";
import { ToolExecutionCard } from "@/components/chat/ToolExecutionCard";
import { ApprovalCard, ApprovalAction } from "@/components/chat/ApprovalCard";
import type { ToolCallEvent, ApprovalEvent } from "@/lib/api-client/types";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const Message = ({ className, from, children, ...props }: MessageProps) => (
  <div
    className={cn(
      "group/msg flex w-full py-1.5 transition-all",
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
        ? "flex flex-col items-end"
        : "w-full text-foreground bg-transparent border-0 px-0 py-1 break-words shadow-none",
      className
    )}
    {...props}
  >
    {children}
  </div>
);

/**
 * Clean, compact User Message bubble (ChatGPT style).
 * Fitted to content with no bottom whitespace, and hover action controls.
 */
export const UserMessage = memo(({ content }: { content: string }) => {
  const [copied, setCopied] = useState(false);

  // Parse optional "Target URL: https://..." prefix
  const { targetUrl, promptText } = useMemo(() => {
    const match = content.match(/^Target URL:\s*([^\n]+)\n*([\s\S]*)$/i);
    if (match) {
      return { targetUrl: match[1].trim(), promptText: match[2].trim() };
    }
    return { targetUrl: null, promptText: content };
  }, [content]);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="group/user flex flex-col items-end max-w-full min-w-0">
      {/* Attached Target URL Pill */}
      {targetUrl && (
        <a
          href={targetUrl.startsWith("http") ? targetUrl : `https://${targetUrl}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1 mb-1.5 rounded-full bg-muted/60 hover:bg-muted/90 border border-border/50 text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors"
        >
          <GlobeIcon className="size-3 text-primary shrink-0" />
          <span className="truncate max-w-[280px]">{targetUrl}</span>
        </a>
      )}

      {/* User Bubble (ChatGPT Style) */}
      <div className="rounded-3xl bg-muted/90 text-foreground border border-border/60 px-4 py-2.5 text-sm leading-relaxed break-words shadow-xs w-fit text-left">
        {promptText || content}
      </div>

      {/* Clean hover action icon outside the bubble */}
      <div className="opacity-0 group-hover/user:opacity-100 transition-opacity flex items-center gap-1 mt-1 px-1">
        <button
          type="button"
          onClick={handleCopy}
          className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer text-xs flex items-center gap-1"
          title="Copy message"
        >
          {copied ? (
            <>
              <CheckIcon className="size-3 text-emerald-500" />
              <span className="text-[10px] text-emerald-500 font-medium">Copied</span>
            </>
          ) : (
            <CopyIcon className="size-3" />
          )}
        </button>
      </div>
    </div>
  );
});

UserMessage.displayName = "UserMessage";

export type MessageResponseProps = {
  content: string;
  toolCalls?: ToolCallEvent[];
  approvals?: ApprovalEvent[];
  isStreaming?: boolean;
  onApproveAction?: (approvalId: string, action: ApprovalAction) => void;
  onRejectAction?: (approvalId: string, action: ApprovalAction) => void;
  onRegenerate?: () => void;
};

/**
 * Enhanced modern AI assistant response renderer with reasoning steps,
 * live Antigravity tool execution cards, approvals, full Markdown, and diagrams.
 */
export const MessageResponse = memo(
  ({
    content,
    toolCalls,
    approvals,
    isStreaming,
    onApproveAction,
    onRejectAction,
    onRegenerate,
  }: MessageResponseProps) => {
    const [copied, setCopied] = useState(false);
    const [liked, setLiked] = useState<boolean | null>(null);
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

      return { reasoning: "", mainContent: content.trim(), isThinkingNow: false };
    }, [content, isStreaming]);

    // Detect if this message contains a panel-worthy artifact
    const artifact = useMemo(() => {
      if (!mainContent || isStreaming) return null;
      return extractArtifact(mainContent);
    }, [mainContent, isStreaming]);

    const handleCopyMessage = () => {
      const plainText = mainContent || content;
      navigator.clipboard.writeText(plainText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    const handleOpenPanel = () => {
      if (artifact) openPanel(artifact);
    };

    // If streaming and not a single token received yet
    if (isStreaming && !content && (!toolCalls || toolCalls.length === 0) && (!approvals || approvals.length === 0)) {
      return (
        <div className="w-full">
          <ReasoningBlock reasoning="" isStreaming={true} />
        </div>
      );
    }

    return (
      <div className="relative w-full space-y-2 font-sans min-w-0">
        {/* Antigravity-Style Live Tool Execution Cards */}
        {toolCalls && toolCalls.length > 0 && (
          <div className="space-y-1.5 my-1.5">
            {toolCalls.map((tc) => (
              <ToolExecutionCard key={tc.tool_id} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Human-in-the-Loop Approval Confirmation Cards */}
        {approvals && approvals.length > 0 && (
          <div className="space-y-1.5 my-1.5">
            {approvals.map((appr) => (
              <ApprovalCard
                key={appr.approval_id}
                approvalId={appr.approval_id}
                action={appr.action}
                onApprove={onApproveAction}
                onReject={onRejectAction}
              />
            ))}
          </div>
        )}

        {/* Dynamic Reasoning / Thought Collapsible Box (Claude / ChatGPT style) */}
        {(reasoning || isThinkingNow) && (
          <ReasoningBlock reasoning={reasoning} isStreaming={isThinkingNow} />
        )}

        {/* Main Response Markdown (renders everything inline directly in chat) */}
        {mainContent && (
          <MarkdownRenderer
            content={mainContent}
            isStreaming={isStreaming && !isThinkingNow}
            suppressInlineArtifacts={false}
          />
        )}

        {/* 
          Optional Artifact Tile (Commented out - side panel disabled for single-pane chat experience):
          {!isStreaming && artifact && <ArtifactCard artifact={artifact} />}
        */}

        {/* Assistant Message action buttons (ChatGPT style) */}
        {!isStreaming && (mainContent || content) && (
          <div className="opacity-0 group-hover/msg:opacity-100 transition-opacity flex items-center gap-1 pt-1.5">
            {/* Copy Button */}
            <Button
              variant="ghost"
              size="icon"
              className="size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
              onClick={handleCopyMessage}
              title="Copy message"
            >
              {copied ? (
                <CheckIcon className="size-3.5 text-emerald-500" />
              ) : (
                <CopyIcon className="size-3.5" />
              )}
            </Button>

            {/* Like */}
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer",
                liked === true && "text-primary bg-primary/10"
              )}
              onClick={() => setLiked(liked === true ? null : true)}
              title="Good response"
            >
              <ThumbsUpIcon className="size-3.5" />
            </Button>

            {/* Dislike */}
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer",
                liked === false && "text-destructive bg-destructive/10"
              )}
              onClick={() => setLiked(liked === false ? null : false)}
              title="Poor response"
            >
              <ThumbsDownIcon className="size-3.5" />
            </Button>

            {/* Regenerate */}
            {onRegenerate && (
              <Button
                variant="ghost"
                size="icon"
                className="size-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
                onClick={onRegenerate}
                title="Regenerate response"
              >
                <RotateCwIcon className="size-3.5" />
              </Button>
            )}

            {/* 
              Open in Artifact Side Panel (Commented out for now):
              {artifact && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-primary cursor-pointer flex items-center gap-1 ml-auto"
                  onClick={handleOpenPanel}
                  title="Open in side panel"
                >
                  <PanelRightOpenIcon className="size-3.5" />
                  <span>Open in panel</span>
                </Button>
              )}
            */}
          </div>
        )}
      </div>
    );
  }
);

MessageResponse.displayName = "MessageResponse";
