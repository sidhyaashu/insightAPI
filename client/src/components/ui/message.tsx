"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { CheckIcon, CopyIcon, TerminalIcon, UserIcon } from "lucide-react";
import type { ComponentProps, HTMLAttributes } from "react";
import { memo, useState } from "react";

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: "user" | "assistant" | "system";
};

export const Message = ({ className, from, children, ...props }: MessageProps) => (
  <div
    className={cn(
      "group flex w-full gap-3",
      from === "user" ? "justify-end" : "justify-start",
      className
    )}
    {...props}
  >
    {from === "assistant" && (
      <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground border border-border/60 mt-1">
        <TerminalIcon className="size-3.5" />
      </div>
    )}

    <div
      className={cn(
        "flex max-w-[85%] flex-col gap-2",
        from === "user" ? "items-end" : "items-start"
      )}
    >
      {children}
    </div>

    {from === "user" && (
      <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground mt-1 shadow-xs">
        <UserIcon className="size-3.5" />
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
      "flex flex-col gap-2 rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs",
      from === "user"
        ? "bg-primary text-primary-foreground rounded-tr-xs"
        : "bg-card text-card-foreground border border-border/60 rounded-tl-xs",
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
};

export const MessageResponse = memo(({ content, isStreaming }: MessageResponseProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group/msg w-full space-y-2">
      <div className="prose prose-sm dark:prose-invert max-w-none break-words whitespace-pre-wrap font-sans text-xs sm:text-sm">
        {content}
        {isStreaming && (
          <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle" />
        )}
      </div>

      <div className="opacity-0 group-hover/msg:opacity-100 transition-opacity flex items-center gap-1 pt-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-muted-foreground hover:text-foreground cursor-pointer"
          onClick={handleCopy}
          title="Copy message"
        >
          {copied ? <CheckIcon className="size-3 text-emerald-500" /> : <CopyIcon className="size-3" />}
        </Button>
      </div>
    </div>
  );
});

MessageResponse.displayName = "MessageResponse";
