"use client";

import { useState, useEffect } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { LockedFeature } from "@/components/ui/LockedFeature";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
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
import { TerminalIcon, BotIcon, GlobeIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
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
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "init-1",
      role: "assistant",
      content: "Hello! I am **InsightAPI Assistant**. Paste a web application URL or ask me to explore REST/GraphQL endpoints, generate OpenAPI documentation, or test route safety guardrails.",
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState("");
  const [activeSteps, setActiveSteps] = useState<AgentProcessStep[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isUrlModalOpen, setIsUrlModalOpen] = useState(false);
  const [targetUrlInput, setTargetUrlInput] = useState("");
  const [activeSettings, setActiveSettings] = useState<CrawlSettings>({
    targetUrl: "",
    maxPages: 15,
    jsRendering: true,
    stealthMode: true,
    model: "gpt-4o-mini",
    authHeader: "",
  });

  const { isConnected, lastMessage, sendMessage } = useWebSocket(`/chat/${sessionId}`);

  // Handle incoming WebSocket messages
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
      settings: activeSettings,
    });
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
    <div className="flex flex-col h-[calc(100vh-7.5rem)] max-w-5xl mx-auto w-full px-4 lg:px-6 py-4">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-3 border-b border-border/60 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-card text-foreground border border-border/60 shadow-xs">
            <TerminalIcon className="size-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
              InsightAPI Intelligence Workspace
              <Badge variant="outline" className="text-[10px] font-mono border-border/60 text-muted-foreground">
                {activeSettings.model}
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
              <span className={`inline-block size-2 rounded-full ${isConnected ? "bg-emerald-500" : "bg-muted-foreground/40"}`} />
              <span>{isConnected ? "Live WebSocket Engine" : "Local Engine"}</span>
              {activeSettings.targetUrl && (
                <span className="ml-2 font-mono text-[11px] text-foreground truncate max-w-[220px] inline-block align-bottom">
                  Target: {activeSettings.targetUrl}
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ConversationDownload messages={messages} />
        </div>
      </div>

      {/* Main Chat Scroll Area */}
      <LockedFeature requiredTier="STARTER" featureName="AI Chatbot" className="flex-1 flex flex-col min-h-0">
        <Conversation className="flex-1 py-4">
          <ConversationContent>
            {messages.length === 0 && (
              <ConversationEmptyState
                icon={<BotIcon className="size-8 text-muted-foreground/40" />}
                title="Start Agent Exploration"
                description="Type a query or click the + icon on the prompt bar to paste a target application URL."
              />
            )}

            {messages.map((m) => (
              <Message key={m.id} from={m.role}>
                <MessageContent from={m.role}>
                  <MessageResponse content={m.content} />
                </MessageContent>
              </Message>
            ))}

            {/* Live Streaming Message & Chain of Thought Steps */}
            {(isStreaming || activeSteps.length > 0) && (
              <Message from="assistant">
                {activeSteps.length > 0 && (
                  <ChainOfThought defaultOpen={true}>
                    <ChainOfThoughtHeader>
                      Reasoning & Process Steps ({activeSteps.filter(s => s.status === "complete").length}/{activeSteps.length} complete)
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

        {/* ChatGPT-style Prompt Input Bar */}
        <div className="pt-2 pb-1 shrink-0">
          <PromptInput
            onSubmit={handleSendMessage}
            onOpenSettings={() => setIsSettingsOpen(true)}
            onOpenPasteUrl={() => setIsUrlModalOpen(true)}
            disabled={isStreaming}
          />
        </div>
      </LockedFeature>

      {/* Crawl & AI Settings Modal */}
      <CrawlSettingsModal
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
        onSave={(newSettings) => setActiveSettings(newSettings)}
        initialSettings={activeSettings}
      />

      {/* Paste Target URL Quick Modal */}
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
