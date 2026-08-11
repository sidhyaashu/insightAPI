"use client";

import React, {
  useState,
  useRef,
  ComponentProps,
  FormEvent,
} from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  PlusIcon,
  SendIcon,
  GlobeIcon,
  SlidersIcon,
  PaperclipIcon,
} from "lucide-react";

export interface PromptInputMessage {
  text: string;
  targetUrl?: string;
}

export type PromptInputProps = Omit<
  ComponentProps<"form">,
  "onSubmit"
> & {
  onSubmit: (message: PromptInputMessage, e: FormEvent) => void;
  onOpenSettings?: () => void;
  onOpenPasteUrl?: () => void;
  disabled?: boolean;
  placeholder?: string;
};

export const PromptInput = ({
  className,
  onSubmit,
  onOpenSettings,
  onOpenPasteUrl,
  disabled = false,
  placeholder = "Ask InsightBot to explore endpoints, generate OpenAPI specs, or paste an app URL...",
  ...props
}: PromptInputProps) => {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSubmit({ text: text.trim() }, e);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative flex flex-col w-full rounded-2xl border border-border/80 bg-card p-2 shadow-lg transition-all focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20",
        className
      )}
      {...props}
    >
      <div className="flex items-end gap-2 px-1">
        {/* + Menu Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="h-9 w-9 flex items-center justify-center rounded-full shrink-0 text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer transition-colors focus:outline-none"
            title="Add target URL or crawl options"
          >
            <PlusIcon className="size-5" />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="start" className="w-56 p-1.5 shadow-xl rounded-xl">
            <DropdownMenuItem
              onClick={onOpenPasteUrl}
              className="cursor-pointer text-xs flex items-center gap-2 py-2"
            >
              <GlobeIcon className="size-4 text-primary" />
              <span>Paste Target Web App URL</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={onOpenSettings}
              className="cursor-pointer text-xs flex items-center gap-2 py-2"
            >
              <SlidersIcon className="size-4 text-purple-400" />
              <span>Crawl & AI Settings</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem className="cursor-pointer text-xs flex items-center gap-2 py-2">
              <PaperclipIcon className="size-4 text-muted-foreground" />
              <span>Attach OpenAPI Spec File</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-44 min-h-[40px] leading-relaxed"
        />

        {/* Send Button */}
        <Button
          type="submit"
          size="icon"
          disabled={disabled || !text.trim()}
          className="h-9 w-9 rounded-full shrink-0 bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-30 cursor-pointer transition-opacity"
        >
          <SendIcon className="size-4" />
        </Button>
      </div>
    </form>
  );
};
