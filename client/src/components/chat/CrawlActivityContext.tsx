"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { securityApi } from "@/features/security/api/security.api";
import { toast } from "sonner";

// --- Event Types ---

export interface CrawlEventItem {
  id: string;
  type:
    | "connected"
    | "log"
    | "page_visited"
    | "endpoint_captured"
    | "form_submitted"
    | "vision_fallback"
    | "humanized_action"
    | "pattern_cache_hit"
    | "pattern_llm_reasoning"
    | "security_test_running"
    | "security_test_outcome"
    | "sandbox_action"
    | "approval_required"
    | "cost_update"
    | "pending_review"
    | "complete"
    | "error";
  timestamp: number;
  data: Record<string, any>;
}

// --- Context Shape ---

interface CrawlActivityContextValue {
  sessionId: string | null;
  targetUrl: string;
  events: CrawlEventItem[];
  isCompleted: boolean;
  isConnected: boolean;
  activeCost: { tokens: number; costUsd: number; cacheHits: number };
  pendingApproval: Record<string, any> | null;
  approving: boolean;
  openCrawlSession: (sessionId: string, targetUrl: string) => void;
  clearCrawlSession: () => void;
  handleApprove: () => Promise<void>;
  handleReject: () => Promise<void>;
}

const CrawlActivityContext = createContext<CrawlActivityContextValue | null>(null);

// --- Provider ---

export function CrawlActivityProvider({
  children,
  onCrawlComplete,
}: {
  children: React.ReactNode;
  onCrawlComplete?: (sessionId: string) => void;
}) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [targetUrl, setTargetUrl] = useState("");
  const [events, setEvents] = useState<CrawlEventItem[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const [activeCost, setActiveCost] = useState({
    tokens: 0,
    costUsd: 0,
    cacheHits: 0,
  });
  const [pendingApproval, setPendingApproval] = useState<Record<string, any> | null>(null);
  const [approving, setApproving] = useState(false);

  const onCrawlCompleteRef = useRef(onCrawlComplete);
  useEffect(() => {
    onCrawlCompleteRef.current = onCrawlComplete;
  }, [onCrawlComplete]);

  const { isConnected, lastMessage } = useWebSocket(
    sessionId ? `/ws/crawls/${sessionId}/stream` : null
  );

  useEffect(() => {
    if (!lastMessage) return;

    const eventType = lastMessage.type || "log";
    const newEvent: CrawlEventItem = {
      id: `evt-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      type: eventType as CrawlEventItem["type"],
      timestamp: Date.now(),
      data: lastMessage,
    };

    setEvents((prev) => [...prev, newEvent]);

    if (eventType === "cost_update") {
      setActiveCost((prev) => ({
        tokens: lastMessage.total_tokens ?? prev.tokens,
        costUsd: lastMessage.total_cost_usd ?? prev.costUsd,
        cacheHits: prev.cacheHits,
      }));
    } else if (eventType === "pattern_cache_hit") {
      setActiveCost((prev) => ({ ...prev, cacheHits: prev.cacheHits + 1 }));
    } else if (eventType === "approval_required") {
      setPendingApproval(lastMessage);
    } else if (eventType === "complete" || eventType === "pending_review") {
      setIsCompleted(true);
      if (sessionId) onCrawlCompleteRef.current?.(sessionId);
    }
  }, [lastMessage, sessionId]);

  const openCrawlSession = useCallback((id: string, url: string) => {
    setSessionId(id);
    setTargetUrl(url);
    setEvents([]);
    setIsCompleted(false);
    setPendingApproval(null);
    setApproving(false);
    setActiveCost({ tokens: 0, costUsd: 0, cacheHits: 0 });
  }, []);

  const clearCrawlSession = useCallback(() => {
    setSessionId(null);
    setTargetUrl("");
    setEvents([]);
    setIsCompleted(false);
    setPendingApproval(null);
    setActiveCost({ tokens: 0, costUsd: 0, cacheHits: 0 });
  }, []);

  const handleApprove = useCallback(async () => {
    if (!pendingApproval?.approval_id) return;
    setApproving(true);
    try {
      await securityApi.approveRun(pendingApproval.approval_id);
      toast.success("Single-use destructive test approved!");
      setPendingApproval(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Approval failed.");
    } finally {
      setApproving(false);
    }
  }, [pendingApproval]);

  const handleReject = useCallback(async () => {
    if (!pendingApproval?.approval_id) return;
    try {
      await securityApi.rejectApproval(pendingApproval.approval_id);
      toast.info("Destructive test cancelled.");
      setPendingApproval(null);
    } catch {
      setPendingApproval(null);
    }
  }, [pendingApproval]);

  return (
    <CrawlActivityContext.Provider
      value={{
        sessionId,
        targetUrl,
        events,
        isCompleted,
        isConnected,
        activeCost,
        pendingApproval,
        approving,
        openCrawlSession,
        clearCrawlSession,
        handleApprove,
        handleReject,
      }}
    >
      {children}
    </CrawlActivityContext.Provider>
  );
}

// --- Hook ---

export function useCrawlActivity(): CrawlActivityContextValue {
  const ctx = useContext(CrawlActivityContext);
  if (!ctx) {
    throw new Error("useCrawlActivity must be used inside <CrawlActivityProvider>");
  }
  return ctx;
}
