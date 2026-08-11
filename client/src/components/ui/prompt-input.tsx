"use client";

import React, { useState, useRef, ComponentProps, FormEvent } from "react";
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
  ArrowUpIcon,
  GlobeIcon,
  SlidersIcon,
  PaperclipIcon,
  MicIcon,
  AudioWaveformIcon,
} from "lucide-react";
import { ClaudeModelSelector, ModelSelection } from "@/components/chat/ClaudeModelSelector";

export interface PromptInputMessage {
  text: string;
  targetUrl?: string;
}

export type PromptInputProps = Omit<ComponentProps<"form">, "onSubmit"> & {
  onSubmit: (message: PromptInputMessage, e: FormEvent) => void;
  onOpenSettings?: () => void;
  onOpenPasteUrl?: () => void;
  disabled?: boolean;
  placeholder?: string;
  modelSelection: ModelSelection;
  onModelSelectionChange: (val: ModelSelection) => void;
};

export const PromptInput = ({
  className,
  onSubmit,
  onOpenSettings,
  onOpenPasteUrl,
  disabled = false,
  placeholder = "How can I help you today?",
  modelSelection,
  onModelSelectionChange,
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
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative flex flex-col w-full rounded-2xl border border-border/80 bg-card p-3 shadow-xl transition-all focus-within:border-border focus-within:ring-1 focus-within:ring-border/40",
        className
      )}
      {...props}
    >
      {/* Top Text Area */}
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="w-full resize-none bg-transparent px-2 py-1 text-sm sm:text-base text-foreground placeholder:text-muted-foreground/60 focus:outline-none max-h-40 min-h-[44px] leading-relaxed"
      />

      {/* Bottom Action Bar */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/30 px-1 mt-1">
        {/* Left: + Menu Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer transition-colors focus:outline-none"
            title="Add target URL, crawl options or files"
          >
            <PlusIcon className="size-4" />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="start" className="w-60 p-1.5 shadow-2xl rounded-xl bg-card border border-border">
            <DropdownMenuItem
              onClick={onOpenPasteUrl}
              className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg"
            >
              <GlobeIcon className="size-4 text-foreground" />
              <span>Paste Target Web App URL</span>
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={onOpenSettings}
              className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg"
            >
              <SlidersIcon className="size-4 text-foreground" />
              <span>Crawl & AI Execution Settings</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg">
              <PaperclipIcon className="size-4 text-muted-foreground" />
              <span>Attach OpenAPI / Postman Spec</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Right: Model Selector + Mic + Send */}
        <div className="flex items-center gap-1.5">
          {/* Claude-style Model & Effort Selector */}
          <ClaudeModelSelector value={modelSelection} onChange={onModelSelectionChange} />

          {/* Voice Input Trigger Icon */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
            title="Voice input"
          >
            <MicIcon className="size-4" />
          </Button>

          {/* Audio Stream Trigger Icon */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
            title="Audio stream"
          >
            <AudioWaveformIcon className="size-4" />
          </Button>

          {/* Send Button */}
          <Button
            type="submit"
            size="icon"
            disabled={disabled || !text.trim()}
            className="h-8 w-8 rounded-lg shrink-0 bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-30 cursor-pointer transition-opacity"
          >
            <ArrowUpIcon className="size-4" />
          </Button>
        </div>
      </div>
    </form>
  );
};
