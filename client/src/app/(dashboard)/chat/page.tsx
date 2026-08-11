"use client";

import { useState, useEffect, useMemo } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { LockedFeature } from "@/components/ui/LockedFeature";
import {
  Conversation,
  ConversationContent,
  ConversationDownload,
  MessageItem,
} from "@/components/ui/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ui/message";
import { PromptInput, PromptInputMessage } from "@/components/ui/prompt-input";
import { ModelSelection } from "@/components/chat/ClaudeModelSelector";
import { FileCodeIcon, ShieldCheckIcon, DownloadIcon, SparklesIcon, TerminalIcon } from "lucide-react";

export default function ChatGPTPage() {
  const [sessionId] = useState(() => `chat-${Date.now()}`);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState("");
  const [modelSelection, setModelSelection] = useState<ModelSelection>({
    model: "gpt-4o-mini",
    effort: "Medium",
  });

  const { isConnected, lastMessage, sendMessage } = useWebSocket(`/chat/${sessionId}`);

  // Dynamic time greeting
  const greetingTitle = useMemo(() => {
    const hour = new Date().getHours();
    if (hour >= 4 && hour < 12) return "Sunlit chat?";
    if (hour >= 12 && hour < 17) return "Afternoon chat?";
    if (hour >= 17 && hour < 21) return "Evening chat?";
    return "Moonlit chat?";
  }, []);

  // Handle incoming WebSocket streaming messages
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "token") {
      setIsStreaming(true);
      setCurrentResponse((prev) => prev + lastMessage.content);
    } else if (lastMessage.type === "done") {
      setIsStreaming(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: currentResponse || lastMessage.content || "Response complete.",
        },
      ]);
      setCurrentResponse("");
    }
  }, [lastMessage, currentResponse]);

  const handleSendMessage = (msg: PromptInputMessage) => {
    if (!msg.text.trim()) return;

    const newMsg: MessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: msg.text,
    };

    setMessages((prev) => [...prev, newMsg]);
    setIsStreaming(true);
    setCurrentResponse("");

    sendMessage({
      message: msg.text,
      model: modelSelection.model,
    });
  };

  const handleActionChipClick = (promptText: string) => {
    handleSendMessage({ text: promptText });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full bg-background text-foreground font-sans">
      <LockedFeature requiredTier="STARTER" featureName="AI Chatbot" className="flex-1 flex flex-col h-full min-h-0">
        {/* State A: Centered Claude Hero View (No Messages Yet) */}
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-3xl mx-auto w-full">
            <div className="flex items-center justify-center gap-3 mb-8">
              <span className="text-3xl sm:text-4xl text-[#e07a5f] font-serif select-none">✳</span>
              <h1 className="text-3xl sm:text-4xl font-serif tracking-tight text-foreground font-normal">
                {greetingTitle}
              </h1>
            </div>

            <div className="w-full mb-6">
              <PromptInput
                onSubmit={handleSendMessage}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
              />
            </div>

            {/* Q&A Suggestion Chips */}
            <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
              <button
                type="button"
                onClick={() => handleActionChipClick("Explain how OpenAPI 3.1 schema generation works")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <FileCodeIcon className="size-3.5 text-muted-foreground" />
                <span>Explain OpenAPI 3.1 Specs</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("How do Two-Tier Risk Guardrails prevent destructive API actions?")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <ShieldCheckIcon className="size-3.5 text-muted-foreground" />
                <span>Two-Tier Guardrails</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("How do I import Postman collections into Postman v10?")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <DownloadIcon className="size-3.5 text-muted-foreground" />
                <span>Postman v2.1 Import Guide</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("What is AXTree Accessibility DOM Distillation?")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <SparklesIcon className="size-3.5 text-muted-foreground" />
                <span>AXTree DOM Architecture</span>
              </button>
            </div>
          </div>
        ) : (
          /* State B: Active Conversation Stream View */
          <div className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full px-4 py-4 min-h-0">
            <div className="flex items-center justify-between pb-3 border-b border-border/60 shrink-0">
              <div className="flex items-center gap-2">
                <TerminalIcon className="size-4 text-muted-foreground" />
                <h2 className="text-xs font-bold font-mono tracking-tight text-foreground">
                  InsightAPI Assistant Session
                </h2>
              </div>
              <ConversationDownload messages={messages} />
            </div>

            <Conversation className="flex-1 py-4">
              <ConversationContent>
                {messages.map((m) => (
                  <Message key={m.id} from={m.role}>
                    <MessageContent from={m.role}>
                      <MessageResponse content={m.content} />
                    </MessageContent>
                  </Message>
                ))}

                {isStreaming && (
                  <Message from="assistant">
                    <MessageContent from="assistant">
                      <MessageResponse content={currentResponse} isStreaming={isStreaming} />
                    </MessageContent>
                  </Message>
                )}
              </ConversationContent>
            </Conversation>

            <div className="pt-2 pb-2 shrink-0">
              <PromptInput
                onSubmit={handleSendMessage}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
              />
            </div>
          </div>
        )}
      </LockedFeature>
    </div>
  );
}
