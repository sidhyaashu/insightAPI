"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsManager, type WSConnection } from "@/lib/api-client/websocket";

export function useWebSocket(path: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const connectionRef = useRef<WSConnection | null>(null);
  const mockTimerRef = useRef<any>(null);

  const isDevMockEnabled = process.env.NODE_ENV === "development" || process.env.NEXT_PUBLIC_ENABLE_MOCK === "true";

  const sendMessage = useCallback((data: any) => {
    if (connectionRef.current && isConnected) {
      connectionRef.current.send(data);
    } else if (isDevMockEnabled) {
      // Mock Fallback response for Chatbot when WS is offline (Dev mode only)
      if (data?.message) {
        setLastMessage({ type: "token", content: `InsightBot (Dev Mock): Received message "${data.message}".` });
        setTimeout(() => {
          setLastMessage({ type: "done", session_id: "mock-session" });
        }, 1000);
      }
    } else {
      setLastMessage({ type: "error", message: "WebSocket connection is offline. Please check service status." });
    }
  }, [isConnected, isDevMockEnabled]);

  useEffect(() => {
    if (!path) return;

    const conn = wsManager.connect(path, {
      onOpen: () => {
        setIsConnected(true);
      },
      onClose: () => {
        setIsConnected(false);
        if (isDevMockEnabled) {
          triggerMockSimulation();
        }
      },
      onMessage: (data) => setLastMessage(data),
      onError: () => {
        setIsConnected(false);
        if (isDevMockEnabled) {
          triggerMockSimulation();
        } else {
          setLastMessage({ type: "error", message: "WebSocket connection failed." });
        }
      },
    });

    connectionRef.current = conn;

    function triggerMockSimulation() {
      setIsConnected(true);
      setLastMessage({ type: "connected", session_id: "mock-session-live" });

      if (path?.includes("/stream")) {
        let count = 0;
        mockTimerRef.current = setInterval(() => {
          count += 1;
          if (count <= 5) {
            setLastMessage({
              type: "log",
              message: `[Dev Mock Engine] Exploration pass ${count} on target routes...`,
              page: count,
              endpoints_found: count * 4,
            });
          } else if (count === 6) {
            setLastMessage({ type: "complete", captured_count: 24 });
            clearInterval(mockTimerRef.current);
          }
        }, 1500);
      }
    }

    return () => {
      conn.close();
      if (mockTimerRef.current) clearInterval(mockTimerRef.current);
      connectionRef.current = null;
      setIsConnected(false);
    };
  }, [path, isDevMockEnabled]);

  return { isConnected, lastMessage, sendMessage };
}
