"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsManager, type WSConnection } from "@/lib/api-client/websocket";

export interface UseWebSocketOptions {
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: (event?: CloseEvent) => void;
  onError?: (event?: Event) => void;
}

export function useWebSocket(path: string | null, options?: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const connectionRef = useRef<WSConnection | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const sendMessage = useCallback((data: any) => {
    if (connectionRef.current && isConnected) {
      connectionRef.current.send(data);
    } else {
      const err = { type: "error", message: "WebSocket connection is offline. Please check service status." };
      setLastMessage(err);
      optionsRef.current?.onMessage?.(err);
    }
  }, [isConnected]);

  useEffect(() => {
    if (!path) return;

    const conn = wsManager.connect(path, {
      onOpen: () => {
        setIsConnected(true);
        optionsRef.current?.onOpen?.();
      },
      onClose: (event?: CloseEvent) => {
        setIsConnected(false);
        optionsRef.current?.onClose?.(event);
        if (event && !event.wasClean && event.code !== 1000 && event.code !== 1005) {
          const err = { type: "error", message: `WebSocket disconnected (code ${event.code}).` };
          setLastMessage(err);
          optionsRef.current?.onMessage?.(err);
        }
      },
      onMessage: (data) => {
        // Immediate synchronous callback execution (prevents dropped high-frequency tokens during React 18/19 state batching)
        optionsRef.current?.onMessage?.(data);
        setLastMessage(data);
      },
      onError: (event?: Event) => {
        setIsConnected(false);
        optionsRef.current?.onError?.(event);
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
