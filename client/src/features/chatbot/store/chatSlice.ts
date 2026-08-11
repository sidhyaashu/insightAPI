import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ChatMessage } from "@/lib/api-client/types";

interface ChatState {
  activeSessionId: string | null;
  messages: ChatMessage[];
  isGenerating: boolean;
  currentStreamContent: string;
}

const initialState: ChatState = {
  activeSessionId: null,
  messages: [],
  isGenerating: false,
  currentStreamContent: "",
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    setChatSession(state, action: PayloadAction<string>) {
      state.activeSessionId = action.payload;
      state.messages = [];
      state.currentStreamContent = "";
    },
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.messages.push(action.payload);
    },
    appendStreamToken(state, action: PayloadAction<string>) {
      state.currentStreamContent += action.payload;
      state.isGenerating = true;
    },
    finalizeStreamMessage(state) {
      if (state.currentStreamContent && state.activeSessionId) {
        state.messages.push({
          id: `msg-${Date.now()}`,
          session_id: state.activeSessionId,
          role: "assistant",
          content: state.currentStreamContent,
          created_at: new Date().toISOString(),
        });
      }
      state.currentStreamContent = "";
      state.isGenerating = false;
    },
    setIsGenerating(state, action: PayloadAction<boolean>) {
      state.isGenerating = action.payload;
    },
  },
});

export const { setChatSession, addMessage, appendStreamToken, finalizeStreamMessage, setIsGenerating } = chatSlice.actions;
export default chatSlice.reducer;
