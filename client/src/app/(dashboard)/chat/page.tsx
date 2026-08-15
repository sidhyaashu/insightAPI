"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useAppSelector, useAppDispatch } from "@/store";
import {
  loadSessionsThunk,
  loadSessionHistoryThunk,
  createSessionThunk,
  resetNewChat,
  updateSessionTitleLocally,
  addMessage,
  appendStreamToken,
  finalizeStreamMessage,
  setIsGenerating,
} from "@/features/chatbot/store/chatSlice";
import {
  Conversation,
  ConversationContent,
  MessageItem,
} from "@/components/ui/conversation";
import { Message, MessageContent, MessageResponse } from "@/components/ui/message";
import { PromptInput, PromptInputMessage } from "@/components/ui/prompt-input";
import { ModelSelection } from "@/components/chat/ClaudeModelSelector";
import {
  FileCodeIcon,
  ShieldCheckIcon,
  DownloadIcon,
  SparklesIcon,
  AlertTriangleIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { CrawlSettingsModal, CrawlSettings } from "@/components/chat/CrawlSettingsModal";
import { CrawlActivityDrawer } from "@/components/chat/CrawlActivityDrawer";
import { crawlsApi } from "@/features/crawls/api/crawls.api";

// Artifact panel
import { ArtifactPanel } from "@/components/chat/ArtifactPanel";
import { ArtifactProvider, useArtifact } from "@/components/chat/ArtifactContext";
import { extractArtifact } from "@/components/chat/artifact-utils";

// ─── Types ─────────────────────────────────────────────────────────────────────

interface ChatQuota {
  tier: string;
  limit: number;
  used: number;
  remaining: number;
  is_exceeded: boolean;
  reset_period: string;
}

// ─── Skeleton loader shown while session history loads from DB ─────────────────

function ChatHistorySkeleton() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 py-12 px-6">
      <div className="w-10 h-10 rounded-2xl bg-muted/60 animate-pulse" />
      <div className="space-y-2 text-center">
        <div className="h-3 w-32 bg-muted/60 rounded-full animate-pulse mx-auto" />
        <div className="h-2 w-24 bg-muted/40 rounded-full animate-pulse mx-auto" />
      </div>
      {[1, 2, 3].map((i) => (
        <div key={i} className="w-full max-w-2xl space-y-2">
          <div
            className={`h-12 rounded-2xl bg-muted/40 animate-pulse ${
              i % 2 === 0 ? "ml-auto w-2/3" : "w-3/4"
            }`}
            style={{ animationDelay: `${i * 120}ms` }}
          />
        </div>
      ))}
    </div>
  );
}

// ─── Inner Chat Component (ChatGPT / Claude URL & Lifecycle Engine) ────────────

function IndustryChatInner() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSessionId = searchParams.get("session");

  // Redux state
  const {
    activeSessionId,
    messages,
    isGenerating,
    currentStreamContent,
    isLoadingHistory,
  } = useAppSelector((state) => state.chat);

  // Local UI state
  const [quota, setQuota] = useState<ChatQuota | null>(null);
  const [quotaExceededMsg, setQuotaExceededMsg] = useState<string | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelSelection>({
    model: "gemini-3.7-flash",
    effort: "Medium",
  });
  const [showCrawlSettingsModal, setShowCrawlSettingsModal] = useState(false);
  const [showCrawlActivityDrawer, setShowCrawlActivityDrawer] = useState(false);
  const [activeCrawlSessionId, setActiveCrawlSessionId] = useState<string | null>(null);
  const [activeCrawlTargetUrl, setActiveCrawlTargetUrl] = useState<string>("");

  const { openPanel } = useArtifact();
  const currentStreamRef = useRef("");
  const pendingMessageRef = useRef<string | null>(null);
  const knownSessionIdRef = useRef<string | null>(null);

  // ── On mount: load sidebar session list from DB ─────────────────────────────
  useEffect(() => {
    dispatch(loadSessionsThunk());
  }, [dispatch]);

  // ── URL synchronization: /chat vs /chat?session=uuid ────────────────────────
  useEffect(() => {
    if (urlSessionId) {
      // If this session was just created by this client sending a message, don't re-fetch!
      if (knownSessionIdRef.current === urlSessionId) {
        return;
      }

      knownSessionIdRef.current = urlSessionId;
      dispatch(loadSessionHistoryThunk(urlSessionId))
        .unwrap()
        .catch(() => {
          toast.error("Session not found. Starting fresh conversation.");
          router.replace("/chat");
        });
    } else {
      // At root /chat: reset to clean state (ChatGPT style)
      if (activeSessionId !== null || knownSessionIdRef.current !== null) {
        knownSessionIdRef.current = null;
        dispatch(resetNewChat());
      }
    }
  }, [urlSessionId, activeSessionId, dispatch, router]);

  // ── WebSocket (opens when activeSessionId exists) ───────────────────────────
  const { lastMessage, sendMessage } = useWebSocket(
    activeSessionId ? `/chat/${activeSessionId}` : null
  );

  // ── Handle WebSocket stream & events ────────────────────────────────────────
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "connected") {
      if (lastMessage.quota) setQuota(lastMessage.quota);

      // If a message was queued while socket was opening, send it now
      if (pendingMessageRef.current) {
        const text = pendingMessageRef.current;
        pendingMessageRef.current = null;
        sendMessage({ message: text, model: modelSelection.model });
      }
    } else if (lastMessage.type === "title") {
      // Real-time title generation received from backend
      if (lastMessage.title && lastMessage.session_id) {
        dispatch(
          updateSessionTitleLocally({
            id: lastMessage.session_id,
            title: lastMessage.title,
          })
        );
      }
    } else if (lastMessage.type === "token") {
      const content = lastMessage.content || "";
      currentStreamRef.current += content;
      dispatch(appendStreamToken(content));
      setQuotaExceededMsg(null);
    } else if (lastMessage.type === "done") {
      if (lastMessage.quota) setQuota(lastMessage.quota);
      dispatch(finalizeStreamMessage());

      // Auto-open artifact side panel if diagram / code artifact detected
      const detected = extractArtifact(currentStreamRef.current);
      if (detected) openPanel(detected);
      currentStreamRef.current = "";
    } else if (lastMessage.type === "quota_exceeded") {
      dispatch(setIsGenerating(false));
      setQuotaExceededMsg(lastMessage.message);
      if (lastMessage.quota) setQuota(lastMessage.quota);
    } else if (lastMessage.type === "error") {
      dispatch(setIsGenerating(false));
      toast.error(lastMessage.message || "An error occurred.");
    }
  }, [lastMessage, dispatch, modelSelection.model, openPanel, sendMessage]);

  // ── Greeting Header ─────────────────────────────────────────────────────────
  const greetingTitle = useMemo(() => {
    const hour = new Date().getHours();
    if (hour >= 4 && hour < 12) return "Good morning, ready to analyze APIs?";
    if (hour >= 12 && hour < 17) return "Good afternoon, what API shall we inspect?";
    if (hour >= 17 && hour < 21) return "Good evening, let's build something great.";
    return "Moonlit intelligence session.";
  }, []);

  // ── Send Message (Atomic DB session creation on first message) ──────────────
  const handleSendMessage = useCallback(
    async (msg: PromptInputMessage) => {
      const text = msg.text.trim();
      if (!text) return;

      if (quota?.is_exceeded && quota.tier !== "ADMIN" && quota.tier !== "ENTERPRISE") {
        setQuotaExceededMsg(
          `Daily message limit (${quota.limit} msgs) reached for your ${quota.tier} plan.`
        );
        return;
      }

      // 1. Optimistically display user message in UI
      dispatch(
        addMessage({
          id: `user-${Date.now()}`,
          session_id: activeSessionId || "pending",
          role: "user",
          content: text,
          created_at: new Date().toISOString(),
        })
      );
      dispatch(setIsGenerating(true));
      currentStreamRef.current = "";
      setQuotaExceededMsg(null);

      // 2. If at root /chat (no session yet), create in DB first and update URL smoothly
      if (!activeSessionId) {
        try {
          const autoTitle = text.slice(0, 50) + (text.length > 50 ? "..." : "");
          const session = await dispatch(createSessionThunk(autoTitle)).unwrap();

          // Mark session ID as known to prevent URL sync from triggering a re-fetch skeleton
          knownSessionIdRef.current = session.id;

          // Queue the message to send over WebSocket once connected
          pendingMessageRef.current = text;

          // Update URL seamlessly
          router.replace(`/chat?session=${session.id}`, { scroll: false });
        } catch {
          dispatch(setIsGenerating(false));
          toast.error("Failed to start conversation. Please try again.");
        }
        return;
      }

      // 3. Existing session — send immediately over WebSocket
      sendMessage({ message: text, model: modelSelection.model });
    },
    [activeSessionId, dispatch, modelSelection.model, quota, router, sendMessage]
  );

  const handleStopStreaming = useCallback(() => {
    dispatch(finalizeStreamMessage());
    currentStreamRef.current = "";
  }, [dispatch]);

  const handleRegenerate = useCallback(() => {
    if (!messages.length || isGenerating) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) handleSendMessage({ text: lastUserMsg.content });
  }, [messages, isGenerating, handleSendMessage]);

  const handleActionChipClick = (promptText: string) => {
    handleSendMessage({ text: promptText });
  };

  const handleExportMarkdown = () => {
    if (!messages.length) return;
    const dateStr = new Date().toISOString().split("T")[0];
    const mdLines = [
      `# InsightAPI AI Conversation Export`,
      `*Date: ${new Date().toLocaleString()}*`,
      `*Session: ${activeSessionId}*`,
      ``,
      `---`,
      ``,
    ];
    messages.forEach((m) => {
      mdLines.push(m.role === "user" ? "### 🧑 User" : "### 🤖 InsightBot");
      mdLines.push(``);
      mdLines.push(m.content);
      mdLines.push(``, `---`, ``);
    });
    const blob = new Blob([mdLines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-${activeSessionId || "session"}-${dateStr}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ── Crawl modal handler ─────────────────────────────────────────────────────
  const handleStartCrawl = async (settings: CrawlSettings) => {
    try {
      toast.loading("Initiating agentic exploration...");
      const res = await crawlsApi.startCrawl({
        target_url: settings.targetUrl,
        max_pages: settings.maxPages,
        goal: undefined,
        require_review: settings.requireReview,
        tos_accepted: settings.tosAccepted,
        auth_profile_id: settings.authProfileId !== "none" ? settings.authProfileId : undefined,
      });
      toast.dismiss();
      toast.success("Autonomous exploration started!");
      setActiveCrawlSessionId(res.session_id || res.id || "");
      setActiveCrawlTargetUrl(settings.targetUrl);
      setShowCrawlActivityDrawer(true);
    } catch (err: any) {
      toast.dismiss();
      toast.error(err.response?.data?.detail || "Failed to start crawl.");
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // Render Layout
  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col flex-1 h-full w-full bg-background text-foreground font-sans overflow-hidden relative">
      {/* Quota exceeded banner */}
      {quotaExceededMsg && (
        <div className="mx-6 mt-4 p-3.5 rounded-2xl border border-destructive/40 bg-destructive/10 text-destructive text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shrink-0 shadow-sm animate-in fade-in z-20">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="size-4 shrink-0" />
            <span>{quotaExceededMsg}</span>
          </div>
          <Link href="/billing">
            <Button
              size="sm"
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 text-xs shrink-0"
            >
              Upgrade Subscription
            </Button>
          </Link>
        </div>
      )}

      {/* ── Two-column layout: [Chat Area] [Artifact Side Panel] ──────────── */}
      <div className="flex flex-1 w-full min-h-0 overflow-hidden">
        {/* ── Main Chat Column ─────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {isLoadingHistory ? (
            <ChatHistorySkeleton />
          ) : messages.length === 0 ? (
            /* ── Hero Welcome Screen (ChatGPT / Claude Style) ──────────── */
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
                  onOpenCrawlModal={() => setShowCrawlSettingsModal(true)}
                  onExportMarkdown={handleExportMarkdown}
                  modelSelection={modelSelection}
                  onModelSelectionChange={setModelSelection}
                  disabled={isGenerating}
                  isStreaming={isGenerating}
                />
              </div>

              {/* Starter Suggestion Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-2xl">
                <button
                  type="button"
                  onClick={() =>
                    handleActionChipClick(
                      "Explain how OpenAPI 3.1 schema generation and parameter normalization work"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20 shrink-0 mt-0.5">
                    <FileCodeIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">
                      OpenAPI 3.1 &amp; Schema Inference
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      Infer route parameters (/users/&#123;id&#125;) and generate valid Swagger schemas.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleActionChipClick(
                      "How do Two-Tier Risk Guardrails prevent destructive API actions like delete or payments?"
                    )
                  }
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
                  onClick={() =>
                    handleActionChipClick(
                      "How do I import and execute Postman Collections v2.1 in Postman or Newman CI/CD?"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20 shrink-0 mt-0.5">
                    <DownloadIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-blue-500 transition-colors">
                      Postman v2.1 &amp; CI/CD Export
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      Export collections directly into Newman automation test suites.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleActionChipClick(
                      "What is AXTree Accessibility DOM Distillation and how does it reduce token consumption?"
                    )
                  }
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
            /* ── Active Conversation Stream ──────────────────────────── */
            <div className="flex-1 flex flex-col h-full w-full min-h-0">
              <Conversation className="flex-1 py-3 overflow-y-auto">
                <ConversationContent>
                  {(messages as MessageItem[]).map((m) => (
                    <Message key={m.id} from={m.role}>
                      <MessageContent from={m.role}>
                        <MessageResponse
                          content={m.content}
                          onRegenerate={m.role === "assistant" ? handleRegenerate : undefined}
                        />
                      </MessageContent>
                    </Message>
                  ))}

                  {isGenerating && (
                    <Message from="assistant">
                      <MessageContent from="assistant">
                        <MessageResponse
                          content={currentStreamContent}
                          isStreaming={isGenerating}
                        />
                      </MessageContent>
                    </Message>
                  )}
                </ConversationContent>
              </Conversation>

              {/* Bottom Centered Prompt Input */}
              <div className="w-full px-4 pt-2 pb-3 shrink-0">
                <div className="max-w-4xl mx-auto w-full">
                  <PromptInput
                    onSubmit={handleSendMessage}
                    onStop={handleStopStreaming}
                    onOpenCrawlModal={() => setShowCrawlSettingsModal(true)}
                    onExportMarkdown={handleExportMarkdown}
                    modelSelection={modelSelection}
                    onModelSelectionChange={setModelSelection}
                    disabled={isGenerating}
                    isStreaming={isGenerating}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Right Artifact Side Panel ─────────────────────────────────── */}
        <ArtifactPanel />
      </div>

      {/* ── Modals ─────────────────────────────────────────────────────────── */}
      <CrawlSettingsModal
        open={showCrawlSettingsModal}
        onOpenChange={setShowCrawlSettingsModal}
        onSave={handleStartCrawl}
      />
      <CrawlActivityDrawer
        open={showCrawlActivityDrawer}
        onOpenChange={setShowCrawlActivityDrawer}
        sessionId={activeCrawlSessionId}
        targetUrl={activeCrawlTargetUrl}
      />
    </div>
  );
}

// ─── Page Wrapper ──────────────────────────────────────────────────────────────

export default function IndustryChatPage() {
  return (
    <ArtifactProvider>
      <IndustryChatInner />
    </ArtifactProvider>
  );
}
