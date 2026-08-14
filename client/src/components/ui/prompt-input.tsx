"use client";

import React, { useState, useRef, ComponentProps, FormEvent, useEffect } from "react";
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
  SquareIcon,
  MicIcon,
  SparklesIcon,
  TerminalIcon,
  PaperclipIcon,
  DownloadIcon,
} from "lucide-react";
import { ClaudeModelSelector, ModelSelection } from "@/components/chat/ClaudeModelSelector";

export interface PromptInputMessage {
  text: string;
  targetUrl?: string;
}

export type PromptInputProps = Omit<ComponentProps<"form">, "onSubmit"> & {
  onSubmit: (message: PromptInputMessage, e: FormEvent) => void;
  onStop?: () => void;
  onOpenPasteUrl?: () => void;
  onExportMarkdown?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  modelSelection: ModelSelection;
  onModelSelectionChange: (val: ModelSelection) => void;
};

export const PromptInput = ({
  className,
  onSubmit,
  onStop,
  onOpenPasteUrl,
  onExportMarkdown,
  disabled = false,
  isStreaming = false,
  placeholder = "Ask about API endpoints, OpenAPI specs, auth flows...",
  modelSelection,
  onModelSelectionChange,
  ...props
}: PromptInputProps) => {
  const [text, setText] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto focus input on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isStreaming) {
      onStop?.();
      return;
    }
    if (!text.trim() || disabled) return;

    let fullText = text.trim();
    if (targetUrl.trim()) {
      fullText = `Target URL: ${targetUrl.trim()}\n\n${fullText}`;
    }

    onSubmit({ text: fullText, targetUrl: targetUrl.trim() || undefined }, e);
    setText("");
    setTargetUrl("");
    setShowUrlInput(false);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    } else if (e.key === "Escape" && isStreaming) {
      e.preventDefault();
      onStop?.();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  // Browser speech recognition (if available)
  const toggleSpeech = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
        }
      };

      recognition.start();
    } catch {}
  };

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "relative flex flex-col w-full rounded-2xl border border-border/80 bg-card p-3 shadow-xl transition-all focus-within:border-primary/60 focus-within:ring-1 focus-within:ring-primary/20",
        className
      )}
      {...props}
    >
      {/* Optional Attached Target URL Chip */}
      {showUrlInput && (
        <div className="flex items-center gap-2 px-2 py-1.5 mb-2 bg-muted/40 rounded-xl border border-border/60 text-xs">
          <GlobeIcon className="size-3.5 text-primary shrink-0" />
          <input
            type="url"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="https://example.com/api"
            className="flex-1 bg-transparent font-mono text-xs focus:outline-none text-foreground placeholder:text-muted-foreground/60"
            autoFocus
          />
          <button
            type="button"
            onClick={() => {
              setTargetUrl("");
              setShowUrlInput(false);
            }}
            className="text-muted-foreground hover:text-foreground text-xs px-1 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Top Text Area */}
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled && !isStreaming}
        rows={1}
        className="w-full resize-none bg-transparent px-2 py-1 text-sm sm:text-base text-foreground placeholder:text-muted-foreground/60 focus:outline-none max-h-48 min-h-[44px] leading-relaxed"
      />

      {/* Bottom Action Bar */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40 px-1 mt-1">
        {/* Left: Quick Attachment Actions */}
        <div className="flex items-center gap-1.5">
          <DropdownMenu>
            <DropdownMenuTrigger
              className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer transition-colors focus:outline-none"
              title="Add Target URL or cURL"
            >
              <PlusIcon className="size-4" />
            </DropdownMenuTrigger>

            <DropdownMenuContent align="start" className="w-64 p-1.5 shadow-2xl rounded-xl bg-card border border-border">
              <DropdownMenuItem
                onClick={() => setShowUrlInput(true)}
                className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg"
              >
                <GlobeIcon className="size-4 text-primary" />
                <span>Attach Target Web App URL</span>
              </DropdownMenuItem>

              <DropdownMenuItem
                onClick={() => setText((prev) => `${prev ? prev + "\n" : ""}curl -X GET "https://api.example.com/v1/users" -H "Authorization: Bearer token"`)}
                className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg"
              >
                <TerminalIcon className="size-4 text-emerald-400" />
                <span>Insert cURL Template</span>
              </DropdownMenuItem>

              {onExportMarkdown && (
                <>
                  <DropdownMenuSeparator className="my-1" />
                  <DropdownMenuItem
                    onClick={onExportMarkdown}
                    className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg text-foreground"
                  >
                    <DownloadIcon className="size-4 text-primary" />
                    <span>Export to Markdown (.md)</span>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Model Selector */}
          <ClaudeModelSelector value={modelSelection} onChange={onModelSelectionChange} />
        </div>

        {/* Right: Dictation + Submit / Stop Button */}
        <div className="flex items-center gap-2">
          {/* Speech Dictation Button */}
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleSpeech}
            className={cn(
              "h-8 w-8 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors cursor-pointer",
              isListening && "text-red-500 bg-red-500/10 animate-pulse"
            )}
            title={isListening ? "Listening..." : "Voice input"}
          >
            <MicIcon className="size-4" />
          </Button>

          {/* Submit or Stop Button */}
          {isStreaming ? (
            <Button
              type="button"
              onClick={onStop}
              size="icon"
              className="h-8 w-8 rounded-xl bg-destructive hover:bg-destructive/90 text-destructive-foreground transition-all shrink-0 cursor-pointer shadow-md animate-pulse"
              title="Stop streaming response (Esc)"
            >
              <SquareIcon className="size-3.5 fill-current" />
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon"
              disabled={!text.trim() || disabled}
              className={cn(
                "h-8 w-8 rounded-xl bg-primary text-primary-foreground transition-all shrink-0 cursor-pointer shadow-xs",
                (!text.trim() || disabled) && "opacity-40 cursor-not-allowed bg-muted text-muted-foreground"
              )}
              title="Send message (Enter)"
            >
              <ArrowUpIcon className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </form>
  );
};
