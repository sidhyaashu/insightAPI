import apiClient from "@/lib/api-client";
import type { ChatSession, SessionWithMessages } from "@/lib/api-client/types";

const BASE = "/v1/chat/sessions";

export const chatSessionsApi = {
  /**
   * Create a new DB-persisted session.
   * Always call this BEFORE opening the WebSocket.
   */
  createSession: async (title = "New Conversation"): Promise<ChatSession> => {
    const { data } = await apiClient.post<ChatSession>(BASE, { title });
    return data;
  },

  /**
   * List all active sessions for the authenticated user.
   * Use this to hydrate the sidebar on mount / refresh.
   */
  listSessions: async (limit = 50, offset = 0): Promise<ChatSession[]> => {
    const { data } = await apiClient.get<ChatSession[]>(
      `${BASE}?limit=${limit}&offset=${offset}`
    );
    return data;
  },

  /**
   * Fetch a single session with its full message history.
   * Use this on page load when ?session=<id> is in the URL.
   */
  getSessionWithMessages: async (sessionId: string): Promise<SessionWithMessages> => {
    const { data } = await apiClient.get<SessionWithMessages>(`${BASE}/${sessionId}`);
    return data;
  },

  /**
   * Rename a session.
   */
  updateTitle: async (sessionId: string, title: string): Promise<ChatSession> => {
    const { data } = await apiClient.patch<ChatSession>(`${BASE}/${sessionId}`, { title });
    return data;
  },

  /**
   * Soft-delete (archive) a session.
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`${BASE}/${sessionId}`);
  },
};
