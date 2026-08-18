"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

// ─── Artifact Types ────────────────────────────────────────────────────────────

export type ArtifactType = "diagram" | "code" | "document" | "table";

export interface Artifact {
  /** Unique id so React can key on it */
  id: string;
  type: ArtifactType;
  /** Display title shown in the panel header */
  title: string;
  /** Raw content (mermaid source, code string, markdown text) */
  content: string;
  /** For code artifacts: the detected language label (e.g. "typescript") */
  language?: string;
}

// ─── Context shape ─────────────────────────────────────────────────────────────

interface ArtifactContextValue {
  artifact: Artifact | null;
  isPanelOpen: boolean;
  openPanel: (a: Artifact) => void;
  closePanel: () => void;
  /** Replace the current artifact without closing/re-opening the panel */
  updateArtifact: (a: Artifact) => void;
}

const ArtifactContext = createContext<ArtifactContextValue | null>(null);

// ─── Provider ──────────────────────────────────────────────────────────────────

export function ArtifactProvider({ children }: { children: React.ReactNode }) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  const openPanel = useCallback((a: Artifact) => {
    setArtifact(a);
    setIsPanelOpen(true);
  }, []);

  const closePanel = useCallback(() => {
    setIsPanelOpen(false);
    // Delay clearing so exit animation can play
    setTimeout(() => setArtifact(null), 300);
  }, []);

  const updateArtifact = useCallback((a: Artifact) => {
    setArtifact(a);
  }, []);

  return (
    <ArtifactContext.Provider value={{ artifact, isPanelOpen, openPanel, closePanel, updateArtifact }}>
      {children}
    </ArtifactContext.Provider>
  );
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export function useArtifact(): ArtifactContextValue {
  const ctx = useContext(ArtifactContext);
  if (!ctx) {
    throw new Error("useArtifact must be used inside <ArtifactProvider>");
  }
  return ctx;
}
