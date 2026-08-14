"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAppSelector } from "@/store";
import {
  Conversation,
  ConversationContent,
  MessageItem,
} from "@/components/ui/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ui/message";
import { PromptInput, PromptInputMessage } from "@/components/ui/prompt-input";
import { ModelSelection } from "@/components/chat/ClaudeModelSelector";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  FileCodeIcon,
  ShieldCheckIcon,
  DownloadIcon,
  SparklesIcon,
  AlertTriangleIcon,
  ZapIcon,
  ArrowRightIcon,
  PlusIcon,
  Trash2Icon,
  MessageSquareIcon,
  HistoryIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ChatQuota {
  tier: string;
  limit: number;
  used: number;
  remaining: number;
  is_exceeded: boolean;
  reset_period: string;
}

interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: MessageItem[];
}

export default function IndustryChatPage() {
  const user = useAppSelector((state) => state.auth.user);
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("insightapi_chat_sessions");
        if (saved) return JSON.parse(saved);
      } catch {}
    }
    const initialId = `chat-${Date.now()}`;
    return [{ id: initialId, title: "New Conversation", createdAt: Date.now(), messages: [] }];
  });

  const [activeSessionId, setActiveSessionId] = useState<string>(() => sessions[0]?.id || `chat-${Date.now()}`);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState("");
  const currentResponseRef = useRef("");
  const [quota, setQuota] = useState<ChatQuota | null>(null);
  const [quotaExceededMsg, setQuotaExceededMsg] = useState<string | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelSelection>({
    model: "gemini-3.7-flash",
    effort: "Medium",
  });

  const activeSession = useMemo(
    () => sessions.find((s) => s.id === activeSessionId) || sessions[0],
    [sessions, activeSessionId]
  );
  const messages = activeSession?.messages || [];

  // Persist sessions to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("insightapi_chat_sessions", JSON.stringify(sessions));
    } catch {}
  }, [sessions]);

  // Connect WebSocket to active session
  const { isConnected, lastMessage, sendMessage } = useWebSocket(`/chat/${activeSessionId}`);

  // Dynamic greeting based on time of day
  const greetingTitle = useMemo(() => {
    const hour = new Date().getHours();
    if (hour >= 4 && hour < 12) return "Good morning, ready to analyze APIs?";
    if (hour >= 12 && hour < 17) return "Good afternoon, what API shall we inspect?";
    if (hour >= 17 && hour < 21) return "Good evening, let's build something great.";
    return "Moonlit intelligence session.";
  }, []);

  // Handle incoming streaming tokens and updates
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "connected" && lastMessage.quota) {
      setQuota(lastMessage.quota);
    } else if (lastMessage.type === "token") {
      setIsStreaming(true);
      setQuotaExceededMsg(null);
      currentResponseRef.current += lastMessage.content || "";
      setCurrentResponse(currentResponseRef.current);
    } else if (lastMessage.type === "done") {
      setIsStreaming(false);
      if (lastMessage.quota) {
        setQuota(lastMessage.quota);
      }

      const finalAssistantContent = currentResponseRef.current || lastMessage.content || "Response complete.";
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [
                ...s.messages,
                {
                  id: `msg-${Date.now()}`,
                  role: "assistant",
                  content: finalAssistantContent,
                },
              ],
            };
          }
          return s;
        })
      );
      currentResponseRef.current = "";
      setCurrentResponse("");
    } else if (lastMessage.type === "quota_exceeded") {
      setIsStreaming(false);
      setQuotaExceededMsg(lastMessage.message);
      if (lastMessage.quota) {
        setQuota(lastMessage.quota);
      }
    }
  }, [lastMessage, activeSessionId]);

  // Start a new chat session
  const handleNewChat = () => {
    const newId = `chat-${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: "New Conversation",
      createdAt: Date.now(),
      messages: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    currentResponseRef.current = "";
    setCurrentResponse("");
    setIsStreaming(false);
    setQuotaExceededMsg(null);
  };

  // Delete a session
  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== id);
      if (filtered.length === 0) {
        const freshId = `chat-${Date.now()}`;
        return [{ id: freshId, title: "New Conversation", createdAt: Date.now(), messages: [] }];
      }
      return filtered;
    });
    if (activeSessionId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
      }
    }
  };

  // Send message
  const handleSendMessage = (msg: PromptInputMessage) => {
    if (!msg.text.trim()) return;

    if (quota && quota.is_exceeded && quota.tier !== "ADMIN" && quota.tier !== "ENTERPRISE") {
      setQuotaExceededMsg(
        `Daily message limit (${quota.limit} msgs) reached for your ${quota.tier} plan. Please upgrade to continue.`
      );
      return;
    }

    const newMsg: MessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: msg.text,
    };

    // Auto update session title on first message
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          const autoTitle = s.messages.length === 0 ? msg.text.slice(0, 32) + (msg.text.length > 32 ? "..." : "") : s.title;
          return {
            ...s,
            title: autoTitle,
            messages: [...s.messages, newMsg],
          };
        }
        return s;
      })
    );

    setIsStreaming(true);
    currentResponseRef.current = "";
    setCurrentResponse("");
    setQuotaExceededMsg(null);

    sendMessage({
      message: msg.text,
      model: modelSelection.model,
    });
  };

  // Stop generation
  const handleStopStreaming = () => {
    setIsStreaming(false);
    const stoppedContent = currentResponseRef.current || currentResponse;
    if (stoppedContent) {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [
                ...s.messages,
                {
                  id: `msg-${Date.now()}`,
                  role: "assistant",
                  content: stoppedContent + " [Generation paused]",
                },
              ],
            };
          }
          return s;
        })
      );
    }
    currentResponseRef.current = "";
    setCurrentResponse("");
  };

  // Regenerate last response
  const handleRegenerate = () => {
    if (messages.length === 0 || isStreaming) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      handleSendMessage({ text: lastUserMsg.content });
    }
  };

  // Suggestion action chips
  const handleActionChipClick = (promptText: string) => {
    handleSendMessage({ text: promptText });
  };

  // Export current conversation to Markdown file (.md)
  const handleExportMarkdown = () => {
    if (!messages || messages.length === 0) return;
    const dateStr = new Date().toISOString().split("T")[0];
    const mdLines = [
      `# InsightAPI AI Conversation Export`,
      `*Date: ${new Date().toLocaleString()}*`,
      `*Session: ${activeSession?.title || activeSessionId}*`,
      ``,
      `---`,
      ``,
    ];

    messages.forEach((m) => {
      const roleLabel = m.role === "user" ? "### 🧑 User" : "### 🤖 InsightBot";
      mdLines.push(roleLabel);
      mdLines.push(``);
      mdLines.push(m.content);
      mdLines.push(``);
      mdLines.push(`---`);
      mdLines.push(``);
    });

    const blob = new Blob([mdLines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chat-${activeSessionId}-${dateStr}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const userTier = quota?.tier || user?.tier || "FREE";
  const usedCount = quota ? quota.used : 0;
  const limitCount = quota ? quota.limit : userTier === "FREE" ? 15 : userTier === "STARTER" ? 50 : 250;
  const remainingCount = quota ? quota.remaining : Math.max(0, limitCount - usedCount);
  const isUnlimited = userTier === "ADMIN" || userTier === "ENTERPRISE" || limitCount >= 5000;
  const quotaPercent = isUnlimited ? 0 : Math.min(100, Math.round((usedCount / limitCount) * 100));

  return (
    <div className="flex flex-col flex-1 h-full w-full bg-background text-foreground font-sans overflow-hidden">
      {/* ONLY ONE Single Unified Top Navbar */}
      <header className="h-12 border-b border-border/40 px-3 bg-card/40 backdrop-blur flex items-center justify-between gap-3 shrink-0 select-none z-10">
        {/* Left: Sidebar Trigger & Chat Controls */}
        <div className="flex items-center gap-2">
          <SidebarTrigger className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition cursor-pointer rounded-lg shrink-0" />

          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            className="h-7 px-2.5 text-xs font-medium bg-card hover:bg-muted/80 text-foreground border-border/60 shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            <PlusIcon className="size-3.5 text-primary" />
            <span>New Chat</span>
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 cursor-pointer"
            title="Chat History"
          >
            <HistoryIcon className="size-3.5" />
            <span className="hidden sm:inline">History ({sessions.length})</span>
          </Button>
        </div>

        {/* Right: SaaS Quota Meter & Theme Toggle */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="outline" className="font-mono text-[10px] uppercase border-primary/40 text-primary bg-primary/10">
              {userTier} PLAN
            </Badge>

            {isUnlimited ? (
              <span className="text-muted-foreground font-mono flex items-center gap-1 text-[11px]">
                <ZapIcon className="size-3 text-emerald-500" /> Unlimited
              </span>
            ) : (
              <div className="flex items-center gap-2 font-mono text-[11px]">
                <div className="w-16 sm:w-24 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      quotaPercent > 80 ? "bg-rose-500" : quotaPercent > 50 ? "bg-amber-500" : "bg-primary"
                    }`}
                    style={{ width: `${quotaPercent}%` }}
                  />
                </div>
                <span className="text-muted-foreground">
                  <strong className="text-foreground">{remainingCount}</strong>/{limitCount} msgs left
                </span>
              </div>
            )}
          </div>

          {!isUnlimited && (
            <Link href="/billing">
              <Button size="sm" variant="ghost" className="h-7 px-2 text-xs text-primary hover:text-primary/80 font-medium flex items-center gap-1">
                <span>Upgrade</span>
                <ArrowRightIcon className="size-3" />
              </Button>
            </Link>
          )}

          <ThemeToggle />
        </div>
      </header>

      {/* Quota Exceeded Alert Notice */}
      {quotaExceededMsg && (
        <div className="mx-4 mt-3 p-3.5 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0 shadow-xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="size-4 shrink-0 text-destructive" />
            <span>{quotaExceededMsg}</span>
          </div>
          <Link href="/billing">
            <Button size="sm" className="bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs shrink-0 font-medium">
              Upgrade Subscription
            </Button>
          </Link>
        </div>
      )}

      {/* Main Chat Workspace Layout */}
      <div className="flex flex-1 w-full min-h-0 overflow-hidden relative">
        {/* Sessions History Drawer */}
        {showHistoryDrawer && (
          <aside className="w-64 border-r border-border/60 bg-muted/10 p-3 flex flex-col gap-2 shrink-0 z-20 transition-all animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between pb-2 border-b border-border/40 text-xs font-semibold text-foreground">
              <span>Saved Conversations</span>
              <button
                type="button"
                onClick={() => setShowHistoryDrawer(false)}
                className="text-muted-foreground hover:text-foreground cursor-pointer px-1"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1 pr-1">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => {
                    setActiveSessionId(s.id);
                    setShowHistoryDrawer(false);
                  }}
                  className={`group flex items-center justify-between p-2 rounded-xl text-xs cursor-pointer transition-colors ${
                    activeSessionId === s.id
                      ? "bg-primary/10 text-primary font-semibold border border-primary/20"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                  }`}
                >
                  <div className="flex items-center gap-2 truncate min-w-0">
                    <MessageSquareIcon className="size-3.5 shrink-0 text-muted-foreground group-hover:text-primary" />
                    <span className="truncate">{s.title}</span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity p-1 cursor-pointer"
                    title="Delete conversation"
                  >
                    <Trash2Icon className="size-3" />
                  </button>
                </div>
              ))}
            </div>
          </aside>
        )}

        {/* State A: Centered Claude Hero View (No Messages in Active Session) */}
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-3xl mx-auto w-full overflow-y-auto no-scrollbar">
            <div className="flex items-center justify-center gap-3 mb-6">
              <span className="text-3xl sm:text-4xl text-primary select-none">✳</span>
              <h1 className="text-2xl sm:text-3xl font-serif tracking-tight text-foreground font-normal text-center">
                {greetingTitle}
              </h1>
            </div>

            <div className="w-full mb-6">
              <PromptInput
                onSubmit={handleSendMessage}
                onStop={handleStopStreaming}
                onExportMarkdown={handleExportMarkdown}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
                isStreaming={isStreaming}
              />
            </div>

            {/* Structured Suggestion Action Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-2xl">
              <button
                type="button"
                onClick={() => handleActionChipClick("Explain how OpenAPI 3.1 schema generation and parameter normalization work")}
                className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
              >
                <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20 shrink-0 mt-0.5">
                  <FileCodeIcon className="size-4" />
                </div>
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">
                    OpenAPI 3.1 & Schema Inference
                  </span>
                  <p className="text-[11px] text-muted-foreground leading-snug">
                    Infer route parameters (/users/&#123;id&#125;) and generate valid Swagger schemas.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("How do Two-Tier Risk Guardrails prevent destructive API actions like delete or payments?")}
                className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
              >
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 shrink-0 mt-0.5">
                  <ShieldCheckIcon className="size-4" />
                </div>
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-foreground group-hover:text-emerald-500 transition-colors">
                    Two-Tier Action Guardrails
                  </span>
                  <p className="text-[11px] text-muted-foreground leading-snug">
                    Prevent dangerous clicks on deletion, billing, and account changes.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("How do I import and execute Postman Collections v2.1 in Postman or Newman CI/CD?")}
                className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
              >
                <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20 shrink-0 mt-0.5">
                  <DownloadIcon className="size-4" />
                </div>
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-foreground group-hover:text-blue-500 transition-colors">
                    Postman v2.1 & CI/CD Export
                  </span>
                  <p className="text-[11px] text-muted-foreground leading-snug">
                    Export collections directly into Newman automation test suites.
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleActionChipClick("What is AXTree Accessibility DOM Distillation and how does it reduce token consumption?")}
                className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
              >
                <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500 border border-purple-500/20 shrink-0 mt-0.5">
                  <SparklesIcon className="size-4" />
                </div>
                <div className="space-y-0.5">
                  <span className="font-semibold text-xs text-foreground group-hover:text-purple-500 transition-colors">
                    AXTree DOM Architecture
                  </span>
                  <p className="text-[11px] text-muted-foreground leading-snug">
                    Distill 100k+ HTML nodes into compact 500-token semantic trees.
                  </p>
                </div>
              </button>
            </div>
          </div>
        ) : (
          /* State B: Active Conversation Stream View (Clean without duplicate sub-headers) */
          <div className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full px-4 py-3 min-h-0">
            <Conversation className="flex-1 py-3 overflow-y-auto">
              <ConversationContent>
                {messages.map((m) => (
                  <Message key={m.id} from={m.role}>
                    <MessageContent from={m.role}>
                      <MessageResponse
                        content={m.content}
                        onRegenerate={m.role === "assistant" ? handleRegenerate : undefined}
                      />
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

            {/* Prompt Input at bottom */}
            <div className="pt-2 pb-1 shrink-0">
              <PromptInput
                onSubmit={handleSendMessage}
                onStop={handleStopStreaming}
                onExportMarkdown={handleExportMarkdown}
                modelSelection={modelSelection}
                onModelSelectionChange={setModelSelection}
                disabled={isStreaming}
                isStreaming={isStreaming}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
