"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsManager, type WSConnection } from "@/lib/api-client/websocket";

export function useWebSocket(path: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const connectionRef = useRef<WSConnection | null>(null);
  const mockTimerRef = useRef<any>(null);

  const sendMessage = useCallback((data: any) => {
    if (connectionRef.current && isConnected) {
      connectionRef.current.send(data);
    } else {
      // Mock Fallback response for Chatbot when WS is offline
      if (data?.message) {
        setLastMessage({ type: "token", content: `InsightBot (Mock Response): I received your message "${data.message}". Since the backend agent service is currently offline, this is a simulated response demonstrating real-time token streaming in your UI development environment.` });
        setTimeout(() => {
          setLastMessage({ type: "done", session_id: "mock-session" });
        }, 1200);
      }
    }
  }, [isConnected]);

  useEffect(() => {
    if (!path) return;

    let wsFailed = false;

    const conn = wsManager.connect(path, {
      onOpen: () => {
        setIsConnected(true);
      },
      onClose: () => {
        setIsConnected(false);
        triggerMockSimulation();
      },
      onMessage: (data) => setLastMessage(data),
      onError: () => {
        setIsConnected(false);
        wsFailed = true;
        triggerMockSimulation();
      },
    });

    connectionRef.current = conn;

    function triggerMockSimulation() {
      // Simulate connection open for smooth UI development
      setIsConnected(true);
      setLastMessage({ type: "connected", session_id: "mock-session-live" });

      if (path?.includes("/stream")) {
        // Simulate live crawl log events
        let count = 0;
        mockTimerRef.current = setInterval(() => {
          count += 1;
          if (count <= 5) {
            setLastMessage({
              type: "log",
              message: `[Mock Agent Engine] Exploration pass ${count} on target routes...`,
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
  }, [path]);

  return { isConnected, lastMessage, sendMessage };
}
