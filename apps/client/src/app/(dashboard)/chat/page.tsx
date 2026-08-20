"use client";

import React, { useState, useEffect, useMemo, useRef, useCallback, Suspense } from "react";
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
  addToolStart,
  updateToolResult,
  addApprovalRequired,
  removeApproval,
  setSelectedAuthProfileId,
  appendStreamToken,
  finalizeStreamMessage,
  setIsGenerating,
} from "@/features/chatbot/store/chatSlice";
import {
  Conversation,
  ConversationContent,
  MessageItem,
} from "@/components/ui/conversation";
import { Message, MessageContent, MessageResponse, UserMessage } from "@/components/ui/message";
import { PromptInput, PromptInputMessage } from "@/components/ui/prompt-input";
import { ModelSelection } from "@/components/chat/ClaudeModelSelector";
import {
  FileCodeIcon,
  ShieldCheckIcon,
  DownloadIcon,
  SparklesIcon,
  AlertTriangleIcon,
  TerminalIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

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
    activeToolCalls,
    activeApprovals,
    isLoadingHistory,
  } = useAppSelector((state) => state.chat);

  // Local UI state
  const [quota, setQuota] = useState<ChatQuota | null>(null);
  const [quotaExceededMsg, setQuotaExceededMsg] = useState<string | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelSelection>({
    model: "gpt-4.1-mini",
    effort: "Medium",
  });

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
      if (knownSessionIdRef.current !== null) {
        knownSessionIdRef.current = null;
        dispatch(resetNewChat());
      }
    }
  }, [urlSessionId, dispatch, router]);

  // ── Handle WebSocket stream & events directly without React state queue loss ────────
  const handleWsMessage = useCallback(
    (msg: any) => {
      if (!msg) return;

      if (msg.type === "connected") {
        if (msg.quota) setQuota(msg.quota);

        if (pendingMessageRef.current) {
          const text = pendingMessageRef.current;
          pendingMessageRef.current = null;
          sendMessage({ message: text, model: modelSelection.model });
        }
      } else if (msg.type === "title") {
        if (msg.title && msg.session_id) {
          dispatch(
            updateSessionTitleLocally({
              id: msg.session_id,
              title: msg.title,
            })
          );
        }
      } else if (msg.type === "tool_start") {
        dispatch(
          addToolStart({
            tool_id: msg.tool_id,
            tool: msg.tool,
            title: msg.title,
            input: msg.input,
          })
        );
      } else if (msg.type === "tool_result") {
        dispatch(
          updateToolResult({
            tool_id: msg.tool_id,
            status: msg.status,
            latency_ms: msg.latency_ms,
            output: msg.output,
            error: msg.error,
          })
        );
      } else if (msg.type === "approval_required") {
        dispatch(
          addApprovalRequired({
            approval_id: msg.approval_id,
            action: msg.action,
          })
        );
      } else if (msg.type === "token") {
        const content = msg.content || "";
        currentStreamRef.current += content;
        dispatch(appendStreamToken(content));
        setQuotaExceededMsg(null);
      } else if (msg.type === "done") {
        if (msg.quota) setQuota(msg.quota);
        dispatch(finalizeStreamMessage());

        // Side panel disabled for single chat pane:
        // const detected = extractArtifact(currentStreamRef.current);
        // if (detected) openPanel(detected);
        currentStreamRef.current = "";
      } else if (msg.type === "quota_exceeded") {
        dispatch(setIsGenerating(false));
        setQuotaExceededMsg(msg.message);
        if (msg.quota) setQuota(msg.quota);
      } else if (msg.type === "error") {
        dispatch(setIsGenerating(false));
        const errText = msg.message || "WebSocket disconnected.";
        toast.error(errText);
        if (!currentStreamRef.current && activeSessionId) {
          dispatch(
            addMessage({
              id: `err-${Date.now()}`,
              session_id: activeSessionId,
              role: "assistant",
              content: `> [!WARNING]\n> **Chat Service Alert**: ${errText}\n\n*Please ensure services are running and your LLM API keys are configured in \`.env\`.*`,
              created_at: new Date().toISOString(),
            })
          );
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [dispatch, modelSelection.model, openPanel, activeSessionId]
  );

  // ── WebSocket (opens when activeSessionId exists) ───────────────────────────
  const { isConnected, sendMessage } = useWebSocket(
    activeSessionId ? `/chat/${activeSessionId}` : null,
    { onMessage: handleWsMessage }
  );

  const handleApproveAction = useCallback(
    (approvalId: string, action: any) => {
      dispatch(removeApproval(approvalId));
      sendMessage({
        message: `Proceed: Run ${action.method} ${action.url}`,
        model: modelSelection.model,
        approved_actions: [`${action.method}:${action.url}`],
      });
      toast.success(`Executing approved ${action.method} probe...`);
    },
    [dispatch, sendMessage, modelSelection.model]
  );

  const handleRejectAction = useCallback(
    (approvalId: string, action: any) => {
      dispatch(removeApproval(approvalId));
      toast.info(`Action ${action.method} ${action.url} skipped.`);
    },
    [dispatch]
  );

  // Send pending queued message immediately when socket becomes connected
  useEffect(() => {
    if (isConnected && pendingMessageRef.current) {
      const text = pendingMessageRef.current;
      pendingMessageRef.current = null;
      sendMessage({ message: text, model: modelSelection.model });
    }
  }, [isConnected, sendMessage, modelSelection.model]);

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

          knownSessionIdRef.current = session.id;
          pendingMessageRef.current = text;
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
                      "Design a comprehensive OpenAPI 3.1 specification for a modern payment and subscriptions API with Stripe webhooks"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20 shrink-0 mt-0.5">
                    <FileCodeIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors">
                      OpenAPI 3.1 Specification Design
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      Generate full schemas, request/response models, and path parameters.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleActionChipClick(
                      "How do I analyze and debug authentication tokens (OAuth2, Bearer JWT, Session Cookies) across microservices?"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 shrink-0 mt-0.5">
                    <ShieldCheckIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-emerald-500 transition-colors">
                      Auth &amp; Security Analysis
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      Inspect JWT headers, rate limiters, CORS policies, and token scopes.
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleActionChipClick(
                      "Generate a Postman Collection v2.1 with dynamic environment variables for a multi-tenant REST API"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-blue-500/10 text-blue-500 border border-blue-500/20 shrink-0 mt-0.5">
                    <DownloadIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-blue-500 transition-colors">
                      Postman v2.1 &amp; CI/CD Collections
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
                      "Parse and test this cURL command, extract its JSON schema, and generate a Mermaid sequence flow:\n\ncurl -X POST 'https://api.example.com/v1/orders' -H 'Authorization: Bearer test_token' -H 'Content-Type: application/json' -d '{\"item_id\": \"item_456\", \"quantity\": 2, \"currency\": \"USD\"}'"
                    )
                  }
                  className="flex items-start gap-3 p-3 rounded-2xl border border-border/60 bg-card hover:bg-muted/60 text-left transition-all cursor-pointer shadow-xs hover:border-primary/40 group"
                >
                  <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500 border border-purple-500/20 shrink-0 mt-0.5">
                    <TerminalIcon className="size-4" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="font-semibold text-xs text-foreground group-hover:text-purple-500 transition-colors">
                      cURL &amp; Request Debugging
                    </span>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      Parse raw cURL requests, infer payloads, and draw architecture diagrams.
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
                      {m.role === "user" ? (
                        <UserMessage content={m.content} />
                      ) : (
                        <MessageResponse
                          content={m.content}
                          toolCalls={m.tool_calls}
                          approvals={m.approvals}
                          onApproveAction={handleApproveAction}
                          onRejectAction={handleRejectAction}
                          onRegenerate={handleRegenerate}
                        />
                      )}
                    </Message>
                  ))}

                  {isGenerating && (
                    <Message from="assistant">
                      <MessageContent from="assistant">
                        <MessageResponse
                          content={currentStreamContent}
                          toolCalls={activeToolCalls}
                          approvals={activeApprovals}
                          onApproveAction={handleApproveAction}
                          onRejectAction={handleRejectAction}
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

        {/* 
          Right Artifact Side Panel (Commented out - all content renders inline in chat):
          <ArtifactPanel />
        */}
      </div>
    </div>
  );
}

// ─── Page Wrapper ──────────────────────────────────────────────────────────────

export default function IndustryChatPage() {
  return (
    <ArtifactProvider>
      <Suspense fallback={<ChatHistorySkeleton />}>
        <IndustryChatInner />
      </Suspense>
    </ArtifactProvider>
  );
}
