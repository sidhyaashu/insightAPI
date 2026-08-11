import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, useSelector, type TypedUseSelectorHook } from "react-redux";
import authReducer from "@/features/auth/store/authSlice";
import crawlsReducer from "@/features/crawls/store/crawlsSlice";
import chatReducer from "@/features/chatbot/store/chatSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    crawls: crawlsReducer,
    chat: chatReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Typed hooks — use these everywhere instead of plain useDispatch / useSelector
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
