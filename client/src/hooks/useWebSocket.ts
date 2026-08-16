"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsManager, type WSConnection } from "@/lib/api-client/websocket";

export function useWebSocket(path: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const connectionRef = useRef<WSConnection | null>(null);

  const sendMessage = useCallback((data: any) => {
    if (connectionRef.current && isConnected) {
      connectionRef.current.send(data);
    } else {
      setLastMessage({ type: "error", message: "WebSocket connection is offline. Please check service status." });
    }
  }, [isConnected]);

  useEffect(() => {
    if (!path) return;

    const conn = wsManager.connect(path, {
      onOpen: () => {
        setIsConnected(true);
      },
      onClose: (event?: CloseEvent) => {
        setIsConnected(false);
        if (event && !event.wasClean && event.code !== 1000 && event.code !== 1005) {
          setLastMessage({ type: "error", message: `WebSocket disconnected (code ${event.code}).` });
        }
      },
      onMessage: (data) => setLastMessage(data),
      onError: () => {
        setIsConnected(false);
      },
    });

    connectionRef.current = conn;

    return () => {
      conn.close();
      connectionRef.current = null;
      setIsConnected(false);
    };
  }, [path]);

  return { isConnected, lastMessage, sendMessage };
}
