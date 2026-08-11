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
      onClose: () => {
        setIsConnected(false);
        setLastMessage({ type: "error", message: "WebSocket connection closed." });
      },
      onMessage: (data) => setLastMessage(data),
      onError: () => {
        setIsConnected(false);
        setLastMessage({ type: "error", message: "WebSocket connection error." });
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
