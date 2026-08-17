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

export interface DiscoveredEndpoint {
  method: string;
  url: string;
  template_route?: string;
  status?: number;
  resource_type?: string;
}

// --- Context Shape ---

interface CrawlActivityContextValue {
  sessionId: string | null;
  targetUrl: string;
  events: CrawlEventItem[];
  isCompleted: boolean;
  isConnected: boolean;
  crawlStatus: "idle" | "running" | "pending_review" | "complete" | "error";
  capturedCount: number;
  capturedEndpoints: DiscoveredEndpoint[];
  errorMessage: string | null;
  activeCost: { tokens: number; costUsd: number; cacheHits: number };
  pendingApproval: Record<string, any> | null;
  approving: boolean;
  openCrawlSession: (sessionId: string, targetUrl: string) => void;
  clearCrawlSession: () => void;
  handleApprove: () => Promise<void>;
  handleReject: () => Promise<void>;
  markCrawlApproved: (session: any) => void;
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
  const [crawlStatus, setCrawlStatus] = useState<"idle" | "running" | "pending_review" | "complete" | "error">("idle");
  const [capturedCount, setCapturedCount] = useState(0);
  const [capturedEndpoints, setCapturedEndpoints] = useState<DiscoveredEndpoint[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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
    sessionId ? `/crawls/${sessionId}/stream` : null
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
    } else if (eventType === "endpoint_captured") {
      setCapturedEndpoints((prev) => {
        const route = lastMessage.template_route || lastMessage.url;
        const exists = prev.some((e) => (e.template_route || e.url) === route && e.method === lastMessage.method);
        if (exists) return prev;
        return [
          ...prev,
          {
            method: lastMessage.method || "GET",
            url: lastMessage.url,
            template_route: lastMessage.template_route,
            status: lastMessage.status,
            resource_type: lastMessage.resource_type,
          },
        ];
      });
      setCapturedCount((prev) => prev + 1);
    } else if (eventType === "pending_review") {
      setIsCompleted(true);
      setCrawlStatus("pending_review");
      if (lastMessage.captured_count !== undefined) {
        setCapturedCount(lastMessage.captured_count);
      }
      if (sessionId) onCrawlCompleteRef.current?.(sessionId);
    } else if (eventType === "complete") {
      setIsCompleted(true);
      setCrawlStatus("complete");
      if (lastMessage.captured_count !== undefined) {
        setCapturedCount(lastMessage.captured_count);
      }
      if (sessionId) onCrawlCompleteRef.current?.(sessionId);
    } else if (eventType === "error") {
      setIsCompleted(true);
      setCrawlStatus("error");
      setErrorMessage(lastMessage.message || "An unexpected error occurred during exploration.");
    }
  }, [lastMessage, sessionId]);

  const openCrawlSession = useCallback((id: string, url: string) => {
    setSessionId(id);
    setTargetUrl(url);
    setEvents([]);
    setIsCompleted(false);
    setCrawlStatus("running");
    setCapturedCount(0);
    setCapturedEndpoints([]);
    setErrorMessage(null);
    setPendingApproval(null);
    setApproving(false);
    setActiveCost({ tokens: 0, costUsd: 0, cacheHits: 0 });
  }, []);

  const clearCrawlSession = useCallback(() => {
    setSessionId(null);
    setTargetUrl("");
    setEvents([]);
    setIsCompleted(false);
    setCrawlStatus("idle");
    setCapturedCount(0);
    setCapturedEndpoints([]);
    setErrorMessage(null);
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

  const markCrawlApproved = useCallback((session: any) => {
    setIsCompleted(true);
    setCrawlStatus("complete");
    if (session?.captured_count !== undefined) {
      setCapturedCount(session.captured_count);
    }
    if (sessionId) {
      onCrawlCompleteRef.current?.(sessionId);
    }
  }, [sessionId]);

  return (
    <CrawlActivityContext.Provider
      value={{
        sessionId,
        targetUrl,
        events,
        isCompleted,
        isConnected,
        crawlStatus,
        capturedCount,
        capturedEndpoints,
        errorMessage,
        activeCost,
        pendingApproval,
        approving,
        openCrawlSession,
        clearCrawlSession,
        handleApprove,
        handleReject,
        markCrawlApproved,
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
