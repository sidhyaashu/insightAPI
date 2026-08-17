import { createSlice, createAsyncThunk, type PayloadAction } from "@reduxjs/toolkit";
import type { ChatMessage, ChatSession, ToolCallEvent, ApprovalEvent } from "@/lib/api-client/types";
import { chatSessionsApi } from "@/features/chatbot/api/chat-sessions.api";

// ─── State ────────────────────────────────────────────────────────────────────

interface ChatState {
  /** Server-fetched session list (source of truth). */
  sessions: ChatSession[];
  /** Currently active session id. */
  activeSessionId: string | null;
  /** Messages for the active session (hydrated from API on switch). */
  messages: ChatMessage[];
  /** True while streaming a response token-by-token. */
  isGenerating: boolean;
  /** Accumulated streaming content for the current response. */
  currentStreamContent: string;
  /** Active live tool executions for the current in-flight assistant response. */
  activeToolCalls: ToolCallEvent[];
  /** Active pending approvals requiring human confirmation. */
  activeApprovals: ApprovalEvent[];
  /** Selected Auth Profile ID to attach to probes. */
  selectedAuthProfileId: string | null;
  /** Loading states. */
  isCreatingSession: boolean;
  isLoadingSessions: boolean;
  isLoadingHistory: boolean;
  /** Error messages. */
  sessionError: string | null;
}

const initialState: ChatState = {
  sessions: [],
  activeSessionId: null,
  messages: [],
  isGenerating: false,
  currentStreamContent: "",
  activeToolCalls: [],
  activeApprovals: [],
  selectedAuthProfileId: null,
  isCreatingSession: false,
  isLoadingSessions: false,
  isLoadingHistory: false,
  sessionError: null,
};

// ─── Async Thunks ─────────────────────────────────────────────────────────────

/** Create a new session on the server, then set it as active. */
export const createSessionThunk = createAsyncThunk<ChatSession, string | undefined>(
  "chat/createSession",
  async (title = "New Conversation") => {
    return await chatSessionsApi.createSession(title);
  }
);

/** Load the full session list for the sidebar. */
export const loadSessionsThunk = createAsyncThunk<ChatSession[]>(
  "chat/loadSessions",
  async () => {
    return await chatSessionsApi.listSessions();
  }
);

/** Load a session + its messages (used on page load / session switch). */
export const loadSessionHistoryThunk = createAsyncThunk<
  { session: ChatSession; messages: ChatMessage[] },
  string
>("chat/loadSessionHistory", async (sessionId) => {
  const data = await chatSessionsApi.getSessionWithMessages(sessionId);
  return { session: data.session, messages: data.messages };
});

/** Delete (archive) a session. */
export const deleteSessionThunk = createAsyncThunk<string, string>(
  "chat/deleteSession",
  async (sessionId) => {
    await chatSessionsApi.deleteSession(sessionId);
    return sessionId;
  }
);

/** Rename a session title. */
export const renameSessionThunk = createAsyncThunk<
  ChatSession,
  { sessionId: string; title: string }
>("chat/renameSession", async ({ sessionId, title }) => {
  return await chatSessionsApi.updateTitle(sessionId, title);
});

// ─── Slice ────────────────────────────────────────────────────────────────────

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    /** Optimistically add a user message to the visible list. */
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    /** Start a live tool execution (shows real-time Antigravity card). */
    addToolStart(
      state,
      action: PayloadAction<{ tool_id: string; tool: string; title?: string; input?: Record<string, unknown> }>
    ) {
      state.isGenerating = true;
      const existing = state.activeToolCalls.find((t) => t.tool_id === action.payload.tool_id);
      if (!existing) {
        state.activeToolCalls.push({
          tool_id: action.payload.tool_id,
          tool: action.payload.tool,
          title: action.payload.title,
          input: action.payload.input,
          status: "running",
        });
      }
    },
    /** Update tool result on completion. */
    updateToolResult(
      state,
      action: PayloadAction<{
        tool_id: string;
        status: "completed" | "failed";
        latency_ms?: number;
        output?: Record<string, unknown>;
        error?: string | null;
      }>
    ) {
      const target = state.activeToolCalls.find((t) => t.tool_id === action.payload.tool_id);
      if (target) {
        target.status = action.payload.status;
        target.latency_ms = action.payload.latency_ms;
        target.output = action.payload.output;
        target.error = action.payload.error;
      }
    },
    addApprovalRequired(state, action: PayloadAction<ApprovalEvent>) {
      state.activeApprovals.push(action.payload);
    },
    removeApproval(state, action: PayloadAction<string>) {
      state.activeApprovals = state.activeApprovals.filter((a) => a.approval_id !== action.payload);
    },
    setSelectedAuthProfileId(state, action: PayloadAction<string | null>) {
      state.selectedAuthProfileId = action.payload;
    },
    /** Accumulate a streaming token. */
    appendStreamToken(state, action: PayloadAction<string>) {
      state.currentStreamContent += action.payload;
      state.isGenerating = true;
    },
    /** Finalize the stream — push the assembled message and clear the buffer. */
    finalizeStreamMessage(state) {
      if ((state.currentStreamContent || state.activeToolCalls.length > 0 || state.activeApprovals.length > 0) && state.activeSessionId) {
        state.messages.push({
          id: `msg-${Date.now()}`,
          session_id: state.activeSessionId,
          role: "assistant",
          content: state.currentStreamContent,
          tool_calls: [...state.activeToolCalls],
          approvals: [...state.activeApprovals],
          created_at: new Date().toISOString(),
        });
      }
      state.currentStreamContent = "";
      state.activeToolCalls = [];
      state.activeApprovals = [];
      state.isGenerating = false;
    },
    setIsGenerating(state, action: PayloadAction<boolean>) {
      state.isGenerating = action.payload;
    },
    clearSessionError(state) {
      state.sessionError = null;
    },
    resetNewChat(state) {
      state.activeSessionId = null;
      state.messages = [];
      state.currentStreamContent = "";
      state.activeToolCalls = [];
      state.activeApprovals = [];
      state.isGenerating = false;
      state.isLoadingHistory = false;
      state.sessionError = null;
    },
    /** Update a session title in the list after the server confirms. */
    updateSessionTitleLocally(state, action: PayloadAction<{ id: string; title: string }>) {
      const s = state.sessions.find((x) => x.id === action.payload.id);
      if (s) s.title = action.payload.title;
    },
  },
  extraReducers: (builder) => {
    // ── createSession ─────────────────────────────────────────────────────────
    builder
      .addCase(createSessionThunk.pending, (state) => {
        state.isCreatingSession = true;
        state.sessionError = null;
      })
      .addCase(createSessionThunk.fulfilled, (state, action) => {
        state.isCreatingSession = false;
        const newSession = action.payload;
        // Prepend to list so it appears at the top
        state.sessions = [newSession, ...state.sessions.filter((s) => s.id !== newSession.id)];
        state.activeSessionId = newSession.id;
        // Preserve optimistic messages if already queued in state
        if (state.messages.length > 0) {
          state.messages = state.messages.map((m) =>
            m.session_id === "pending" || !m.session_id ? { ...m, session_id: newSession.id } : m
          );
        } else {
          state.messages = [];
          state.currentStreamContent = "";
          state.isGenerating = false;
        }
      })
      .addCase(createSessionThunk.rejected, (state, action) => {
        state.isCreatingSession = false;
        state.sessionError = action.error.message || "Failed to create session";
      });

    // ── loadSessions ──────────────────────────────────────────────────────────
    builder
      .addCase(loadSessionsThunk.pending, (state) => {
        state.isLoadingSessions = true;
      })
      .addCase(loadSessionsThunk.fulfilled, (state, action) => {
        state.isLoadingSessions = false;
        state.sessions = action.payload;
      })
      .addCase(loadSessionsThunk.rejected, (state) => {
        state.isLoadingSessions = false;
        // Sidebar gracefully stays empty; no error banner needed
      });

    // ── loadSessionHistory ────────────────────────────────────────────────────
    builder
      .addCase(loadSessionHistoryThunk.pending, (state, action) => {
        const targetId = action.meta.arg;
        if (state.activeSessionId !== targetId) {
          state.isLoadingHistory = true;
          state.messages = [];
          state.currentStreamContent = "";
        }
      })
      .addCase(loadSessionHistoryThunk.fulfilled, (state, action) => {
        state.isLoadingHistory = false;
        state.activeSessionId = action.payload.session.id;
        // If we already have optimistic messages that are generating, merge them intelligently
        if (state.isGenerating && state.messages.length > action.payload.messages.length) {
          // Keep current generating state
        } else {
          state.messages = action.payload.messages;
        }
        // Update session in list if present
        const idx = state.sessions.findIndex((s) => s.id === action.payload.session.id);
        if (idx >= 0) {
          state.sessions[idx] = action.payload.session;
        } else {
          state.sessions = [action.payload.session, ...state.sessions];
        }
      })
      .addCase(loadSessionHistoryThunk.rejected, (state) => {
        state.isLoadingHistory = false;
        state.sessionError = "Failed to load conversation history.";
      });

    // ── deleteSession ─────────────────────────────────────────────────────────
    builder
      .addCase(deleteSessionThunk.fulfilled, (state, action) => {
        state.sessions = state.sessions.filter((s) => s.id !== action.payload);
        if (state.activeSessionId === action.payload) {
          state.activeSessionId = state.sessions[0]?.id || null;
          state.messages = [];
        }
      });

    // ── renameSession ─────────────────────────────────────────────────────────
    builder
      .addCase(renameSessionThunk.fulfilled, (state, action) => {
        const idx = state.sessions.findIndex((s) => s.id === action.payload.id);
        if (idx >= 0) state.sessions[idx] = action.payload;
      });
  },
});

export const {
  addMessage,
  addToolStart,
  updateToolResult,
  addApprovalRequired,
  removeApproval,
  setSelectedAuthProfileId,
  appendStreamToken,
  finalizeStreamMessage,
  setIsGenerating,
  clearSessionError,
  resetNewChat,
  updateSessionTitleLocally,
} = chatSlice.actions;

// Keep legacy export names for backward compat
export const setChatSession = (id: string) => ({ type: "chat/noop", payload: id });

export default chatSlice.reducer;
