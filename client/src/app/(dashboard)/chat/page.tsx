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
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
  ChainOfThoughtContent,
  ChainOfThoughtSearchResults,
  ChainOfThoughtSearchResult,
} from "@/components/ui/chain-of-thought";
import { PromptInput, PromptInputMessage } from "@/components/ui/prompt-input";
import { CrawlSettingsModal, CrawlSettings } from "@/components/chat/CrawlSettingsModal";
import { ModelSelection } from "@/components/chat/ClaudeModelSelector";
import { GlobeIcon, FileCodeIcon, ShieldCheckIcon, DownloadIcon, SparklesIcon, TerminalIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

interface AgentProcessStep {
  id: string;
  label: string;
  description: string;
  status: "complete" | "active" | "pending";
  tags?: string[];
}

export default function ChatGPTPage() {
  const [sessionId] = useState(() => `chat-${Date.now()}`);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState("");
  const [activeSteps, setActiveSteps] = useState<AgentProcessStep[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isUrlModalOpen, setIsUrlModalOpen] = useState(false);
  const [targetUrlInput, setTargetUrlInput] = useState("");
  const [modelSelection, setModelSelection] = useState<ModelSelection>({
    model: "gpt-4o-mini",
    effort: "Medium",
  });
  const [activeSettings, setActiveSettings] = useState<CrawlSettings>({
    targetUrl: "",
    maxPages: 15,
    jsRendering: true,
    stealthMode: true,
    model: "gpt-4o-mini",
    authHeader: "",
  });

  const { isConnected, lastMessage, sendMessage } = useWebSocket(`/chat/${sessionId}`);

  // Dynamic time greeting (e.g. Moonlit chat?, Sunlit chat?, Evening chat?)
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

    if (lastMessage.type === "step") {
      setActiveSteps((prev) => {
        const existing = prev.find((s) => s.id === lastMessage.step_id);
        if (existing) {
          return prev.map((s) =>
            s.id === lastMessage.step_id
              ? { ...s, status: lastMessage.status, description: lastMessage.description }
              : s
          );
        }
        return [
          ...prev,
          {
            id: lastMessage.step_id || `step-${Date.now()}`,
            label: lastMessage.label || "Agent Reasoning Step",
            description: lastMessage.description || "Processing DOM accessibility tree...",
            status: lastMessage.status || "active",
            tags: lastMessage.tags || [],
          },
        ];
      });
    } else if (lastMessage.type === "token") {
      setIsStreaming(true);
      setCurrentResponse((prev) => prev + lastMessage.content);
    } else if (lastMessage.type === "done") {
      setIsStreaming(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: currentResponse || lastMessage.content || "Agent execution complete.",
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

    // Initial mock process steps for visual execution feedback
    setActiveSteps([
      {
        id: "step-1",
        label: "AXTree DOM Snapshot Distillation",
        description: "Filtering raw HTML into interactive accessibility tree (a, button, input, select)...",
        status: "complete",
        tags: ["DOM Snapshot", "Sub-100k Tokens"],
      },
      {
        id: "step-2",
        label: "Two-Tier Risk Classifier Evaluation",
        description: "Pre-filtering safety guardrails: SAFE navigation target vs UNSAFE destructive action.",
        status: "active",
        tags: ["Tier 1 Guardrail", "Tier 2 Context"],
      },
    ]);

    sendMessage({
      message: msg.text,
      target_url: activeSettings.targetUrl,
      settings: { ...activeSettings, model: modelSelection.model },
    });
  };

  const handleActionChipClick = (promptText: string) => {
    if (promptText.includes("URL")) {
      setIsUrlModalOpen(true);
    } else {
      handleSendMessage({ text: promptText });
    }
  };

  const handleApplyUrl = () => {
    if (!targetUrlInput.trim()) return;
    setActiveSettings((prev) => ({ ...prev, targetUrl: targetUrlInput }));
    setIsUrlModalOpen(false);

    handleSendMessage({
      text: `Start autonomous API discovery and OpenAPI documentation generation for target URL: ${targetUrlInput}`,
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full bg-background text-foreground font-sans">
      <LockedFeature requiredTier="STARTER" featureName="AI Chatbot" className="flex-1 flex flex-col h-full min-h-0">
        {/* State A: Centered Claude Hero View (No Messages Yet) */}
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-3xl mx-auto w-full">
            {/* Dynamic Claude Greeting */}
            <div className="flex items-center justify-center gap-3 mb-8">
              <span className="text-3xl sm:text-4xl text-[#e07a5f] font-serif select-none">✳</span>
              <h1 className="text-3xl sm:text-4xl font-serif tracking-tight text-foreground font-normal">
                {greetingTitle}
              </h1>
            </div>

            {/* Floating Claude Prompt Container */}
            <div className="w-full mb-6">
              <PromptInput
                onSubmit={handleSendMessage}
                onOpenSettings={() => setIsSettingsOpen(true)}
                onOpenPasteUrl={() => setIsUrlModalOpen(true)}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
              />
            </div>

            {/* Platform Quick Action Suggestion Chips */}
            <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
              <button
                type="button"
                onClick={() => handleActionChipClick("Explore Web App URL")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <GlobeIcon className="size-3.5 text-muted-foreground" />
                <span>Explore Target URL</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("Generate OpenAPI 3.1 Specification for API endpoints")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <FileCodeIcon className="size-3.5 text-muted-foreground" />
                <span>Generate OpenAPI 3.1</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("Test Two-Tier Action Safety Guardrails")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <ShieldCheckIcon className="size-3.5 text-muted-foreground" />
                <span>Safety Guardrails</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("Export Postman Collection for endpoints")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <DownloadIcon className="size-3.5 text-muted-foreground" />
                <span>Export Postman v2.1</span>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("Explain AXTree Accessibility Snapshotting architecture")}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border/60 bg-card hover:bg-muted/80 text-xs font-medium text-foreground transition-colors cursor-pointer shadow-xs"
              >
                <SparklesIcon className="size-3.5 text-muted-foreground" />
                <span>AXTree Architecture</span>
              </button>
            </div>
          </div>
        ) : (
          /* State B: Active Conversation Stream View */
          <div className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full px-4 py-4 min-h-0">
            {/* Header bar */}
            <div className="flex items-center justify-between pb-3 border-b border-border/60 shrink-0">
              <div className="flex items-center gap-2">
                <TerminalIcon className="size-4 text-muted-foreground" />
                <h2 className="text-xs font-bold font-mono tracking-tight text-foreground">
                  InsightAPI Stream Session
                </h2>
                {activeSettings.targetUrl && (
                  <span className="text-[11px] font-mono text-muted-foreground truncate max-w-[200px]">
                    ({activeSettings.targetUrl})
                  </span>
                )}
              </div>
              <ConversationDownload messages={messages} />
            </div>

            {/* Messages Log */}
            <Conversation className="flex-1 py-4">
              <ConversationContent>
                {messages.map((m) => (
                  <Message key={m.id} from={m.role}>
                    <MessageContent from={m.role}>
                      <MessageResponse content={m.content} />
                    </MessageContent>
                  </Message>
                ))}

                {(isStreaming || activeSteps.length > 0) && (
                  <Message from="assistant">
                    {activeSteps.length > 0 && (
                      <ChainOfThought defaultOpen={true}>
                        <ChainOfThoughtHeader>
                          Reasoning & Execution Steps ({activeSteps.filter((s) => s.status === "complete").length}/{activeSteps.length} complete)
                        </ChainOfThoughtHeader>
                        <ChainOfThoughtContent>
                          {activeSteps.map((step) => (
                            <ChainOfThoughtStep
                              key={step.id}
                              label={step.label}
                              description={step.description}
                              status={step.status}
                            >
                              {step.tags && step.tags.length > 0 && (
                                <ChainOfThoughtSearchResults>
                                  {step.tags.map((tag, idx) => (
                                    <ChainOfThoughtSearchResult key={idx}>
                                      {tag}
                                    </ChainOfThoughtSearchResult>
                                  ))}
                                </ChainOfThoughtSearchResults>
                              )}
                            </ChainOfThoughtStep>
                          ))}
                        </ChainOfThoughtContent>
                      </ChainOfThought>
                    )}

                    {currentResponse && (
                      <MessageContent from="assistant">
                        <MessageResponse content={currentResponse} isStreaming={isStreaming} />
                      </MessageContent>
                    )}
                  </Message>
                )}
              </ConversationContent>
            </Conversation>

            {/* Bottom Floating Prompt Input */}
            <div className="pt-2 pb-2 shrink-0">
              <PromptInput
                onSubmit={handleSendMessage}
                onOpenSettings={() => setIsSettingsOpen(true)}
                onOpenPasteUrl={() => setIsUrlModalOpen(true)}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
              />
            </div>
          </div>
        )}
      </LockedFeature>

      {/* Crawl Settings Modal */}
      <CrawlSettingsModal
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
        onSave={(newSettings) => setActiveSettings(newSettings)}
        initialSettings={activeSettings}
      />

      {/* Quick Target URL Modal */}
      <Dialog open={isUrlModalOpen} onOpenChange={setIsUrlModalOpen}>
        <DialogContent className="max-w-md p-6 rounded-2xl shadow-xl bg-card text-card-foreground border border-border/60">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <GlobeIcon className="size-4 text-foreground" />
              Paste Target Web App URL
            </DialogTitle>
          </DialogHeader>
          <div className="py-3 space-y-2">
            <p className="text-xs text-muted-foreground">
              Enter the root URL of the web application or REST API you want InsightAPI to explore:
            </p>
            <Input
              placeholder="https://native-hurt-progeny.ngrok-free.dev"
              value={targetUrlInput}
              onChange={(e) => setTargetUrlInput(e.target.value)}
              className="text-xs font-mono"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setIsUrlModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleApplyUrl} className="bg-primary text-primary-foreground">
              Explore Target URL
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
