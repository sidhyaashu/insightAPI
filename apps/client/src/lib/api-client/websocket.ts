/**
 * Centralized WebSocket manager.
 * All WebSocket connections in the app go through this singleton.
 * Reads base URL from typed env accessor (NEXT_PUBLIC_WS_BASE_URL).
 */
import env from "@/lib/env";

export interface WSHandlers {
  onMessage: (data: unknown) => void;
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
}

export interface WSConnection {
  id: string;
  send: (data: object) => void;
  close: () => void;
}

class WebSocketManager {
  private connections = new Map<string, WebSocket>();

  /**
   * Open a WebSocket connection to the gateway.
   * The access token is appended as ?token= query param for WS auth.
   *
   * @param path - WS path, e.g. "/crawls/{id}/stream" or "/chat/{session}"
   * @param handlers - Event handlers for the connection
   * @returns WSConnection object with send/close controls
   */
  connect(path: string, handlers: WSHandlers): WSConnection {
    // Clean path if caller prefixed with /ws or ws/ to prevent double /ws/ws/
    const cleanPath = path.replace(/^\/?(ws\/)+/, "");
    const normalizedPath = cleanPath.startsWith("/") ? cleanPath : `/${cleanPath}`;
    const url = path.startsWith("ws://") || path.startsWith("wss://") ? path : `${env.WS_BASE_URL}${normalizedPath}`;
    const id = `ws-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      handlers.onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handlers.onMessage(data);
      } catch {
        handlers.onMessage(event.data);
      }
    };

    ws.onclose = (event) => {
      this.connections.delete(id);
      handlers.onClose?.(event);
    };

    ws.onerror = (event) => {
      handlers.onError?.(event);
    };

    this.connections.set(id, ws);

    return {
      id,
      send: (data: object) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(data));
        }
      },
      close: () => {
        ws.close();
        this.connections.delete(id);
      },
    };
  }

  disconnect(id: string): void {
    const ws = this.connections.get(id);
    if (ws) {
      ws.close();
      this.connections.delete(id);
    }
  }

  disconnectAll(): void {
    this.connections.forEach((ws) => ws.close());
    this.connections.clear();
  }
}

// Singleton — import this everywhere WS is needed
export const wsManager = new WebSocketManager();
