"use client";

import React, { useState, useRef, ComponentProps, FormEvent, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  PlusIcon,
  ArrowUpIcon,
  SquareIcon,
  MicIcon,
  DownloadIcon,
  PaperclipIcon,
  FileCodeIcon,
} from "lucide-react";
import { ClaudeModelSelector, ModelSelection } from "@/components/chat/ClaudeModelSelector";
import { toast } from "sonner";

export interface PromptInputMessage {
  text: string;
}

export type PromptInputProps = Omit<ComponentProps<"form">, "onSubmit"> & {
  onSubmit: (message: PromptInputMessage, e: FormEvent) => void;
  onStop?: () => void;
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
  onExportMarkdown,
  disabled = false,
  isStreaming = false,
  placeholder = "Ask about API endpoints, OpenAPI specs, auth flows, cURL commands...",
  modelSelection,
  onModelSelectionChange,
  ...props
}: PromptInputProps) => {
  const [text, setText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto focus input on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleFileUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      if (content) {
        setText((prev) =>
          prev
            ? `${prev}\n\n[Attached File: ${file.name}]\n${content}`
            : `Please analyze this attached ${file.name} API network traffic and generate an OpenAPI 3.1 specification:\n\n${content}`
        );
        toast.success(`Attached ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
      }
    };
    reader.readAsText(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isStreaming) {
      onStop?.();
      return;
    }
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
    } else if (e.key === "Escape" && isStreaming) {
      e.preventDefault();
      onStop?.();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
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
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative flex flex-col w-full rounded-3xl border border-border/60 bg-muted/25 hover:bg-muted/35 focus-within:bg-card focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20 p-3 shadow-lg transition-all backdrop-blur-md",
        isDragging && "border-primary bg-primary/10 ring-2 ring-primary/30",
        className
      )}
      {...props}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".har,.json,.yaml,.yml,.txt"
        onChange={handleFileChange}
        className="hidden"
      />
      {/* Top Text Area */}
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled && !isStreaming}
        rows={1}
        className="w-full resize-none bg-transparent px-2 py-1 text-sm sm:text-base text-foreground placeholder:text-muted-foreground/60 focus:outline-none max-h-52 min-h-[44px] leading-relaxed font-sans"
      />

      {/* Bottom Action Bar */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40 px-1 mt-1">
        {/* Left: Model Selector & Actions */}
        <div className="flex items-center gap-1.5">
          <DropdownMenu>
            <DropdownMenuTrigger
              className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer transition-colors focus:outline-none"
              title="Options & Attachments"
            >
              <PlusIcon className="size-4" />
            </DropdownMenuTrigger>

            <DropdownMenuContent align="start" className="w-56 p-1.5 shadow-2xl rounded-xl bg-card border border-border">
              <DropdownMenuItem
                onClick={() => fileInputRef.current?.click()}
                className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg text-foreground"
              >
                <PaperclipIcon className="size-4 text-purple-500" />
                <span>Attach .HAR or Spec File</span>
              </DropdownMenuItem>

              {onExportMarkdown && (
                <DropdownMenuItem
                  onClick={onExportMarkdown}
                  className="cursor-pointer text-xs flex items-center gap-2 py-2 rounded-lg text-foreground"
                >
                  <DownloadIcon className="size-4 text-primary" />
                  <span>Export to Markdown (.md)</span>
                </DropdownMenuItem>
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
              className="size-8 rounded-full bg-destructive hover:bg-destructive/90 text-destructive-foreground transition-all shrink-0 cursor-pointer shadow-md animate-pulse"
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
                "size-8 rounded-full bg-primary text-primary-foreground transition-all shrink-0 cursor-pointer shadow-xs",
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
