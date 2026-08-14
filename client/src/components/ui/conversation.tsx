"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { DownloadIcon } from "lucide-react";
import type { ComponentProps } from "react";
import { useCallback, useRef } from "react";

export type MessageItem = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
};

export type ConversationProps = ComponentProps<"div">;

export const Conversation = ({ className, children, ...props }: ConversationProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={containerRef}
      className={cn("relative flex-1 overflow-y-auto pr-2 scroll-smooth no-scrollbar", className)}
      role="log"
      {...props}
    >
      {children}
    </div>
  );
};

export type ConversationContentProps = ComponentProps<"div">;

export const ConversationContent = ({ className, ...props }: ConversationContentProps) => (
  <div className={cn("flex flex-col gap-5 p-2 sm:p-4 max-w-4xl mx-auto pb-12 w-full min-w-0", className)} {...props} />
);

export type ConversationEmptyStateProps = ComponentProps<"div"> & {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
};

export const ConversationEmptyState = ({
  className,
  title = "No messages yet",
  description = "Start a conversation or paste an application URL below.",
  icon,
  children,
  ...props
}: ConversationEmptyStateProps) => (
  <div
    className={cn(
      "flex size-full min-h-[300px] flex-col items-center justify-center gap-3 p-8 text-center",
      className
    )}
    {...props}
  >
    {children ?? (
      <>
        {icon && <div className="text-muted-foreground/60">{icon}</div>}
        <div className="space-y-1">
          <h3 className="font-semibold text-base text-foreground">{title}</h3>
          {description && (
            <p className="text-muted-foreground text-xs max-w-md leading-relaxed">{description}</p>
          )}
        </div>
      </>
    )}
  </div>
);

export type ConversationDownloadProps = Omit<ComponentProps<typeof Button>, "onClick"> & {
  messages: MessageItem[];
  filename?: string;
};

export const messagesToMarkdown = (messages: MessageItem[]): string =>
  messages
    .map((msg) => `### **${msg.role.toUpperCase()}:**\n${msg.content}`)
    .join("\n\n---\n\n");

export const ConversationDownload = ({
  messages,
  filename = "insightapi-chat.md",
  className,
  children,
  ...props
}: ConversationDownloadProps) => {
  const handleDownload = useCallback(() => {
    const markdown = messagesToMarkdown(messages);
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, [messages, filename]);

  return (
    <Button
      className={cn("rounded-lg dark:bg-card dark:hover:bg-muted cursor-pointer", className)}
      onClick={handleDownload}
      size="sm"
      type="button"
      variant="outline"
      {...props}
    >
      {children ?? (
        <>
          <DownloadIcon className="size-3.5 mr-1.5" /> Export Markdown
        </>
      )}
    </Button>
  );
};
