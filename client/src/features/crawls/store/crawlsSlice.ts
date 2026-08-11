import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { CrawlSession } from "@/lib/api-client/types";

interface CrawlsState {
  activeSession: CrawlSession | null;
  logs: Array<{ type: string; message?: string; page?: number; endpoints_found?: number }>;
  history: CrawlSession[];
  isStreaming: boolean;
}

const initialState: CrawlsState = {
  activeSession: null,
  logs: [],
  history: [],
  isStreaming: false,
};

const crawlsSlice = createSlice({
  name: "crawls",
  initialState,
  reducers: {
    setActiveSession(state, action: PayloadAction<CrawlSession | null>) {
      state.activeSession = action.payload;
      state.logs = [];
    },
    appendLog(state, action: PayloadAction<any>) {
      state.logs.push(action.payload);
    },
    setIsStreaming(state, action: PayloadAction<boolean>) {
      state.isStreaming = action.payload;
    },
    setHistory(state, action: PayloadAction<CrawlSession[]>) {
      state.history = action.payload;
    },
  },
});

export const { setActiveSession, appendLog, setIsStreaming, setHistory } = crawlsSlice.actions;
export default crawlsSlice.reducer;
