"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { ExternalLinkIcon } from "lucide-react";
import type { Artifact } from "./ArtifactContext";
import { useArtifact } from "./ArtifactContext";
import { artifactBadgeLabel } from "./artifact-utils";

interface ArtifactCardProps {
  artifact: Artifact;
  className?: string;
}

/**
 * Clean, minimal inline Artifact Card in the chat stream (Claude style).
 * No tacky logos, just clean typography, minimal badge, and action link.
 */
export function ArtifactCard({ artifact, className }: ArtifactCardProps) {
  const { openPanel, artifact: activeArtifact, isPanelOpen } = useArtifact();
  const isCurrentlyOpen = isPanelOpen && activeArtifact?.id === artifact.id;

  return (
    <button
      type="button"
      onClick={() => openPanel(artifact)}
      className={cn(
        "group w-full my-2.5 flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl border transition-all cursor-pointer text-left select-none",
        isCurrentlyOpen
          ? "border-primary/40 bg-primary/5 shadow-xs"
          : "border-border/40 bg-muted/20 hover:border-border/80 hover:bg-muted/40",
        className
      )}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="font-semibold text-xs text-foreground truncate">
          {artifact.title}
        </span>
        <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded-md bg-muted/80 text-muted-foreground border border-border/40 font-normal">
          {artifactBadgeLabel(artifact.type, artifact.language)}
        </span>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-muted-foreground group-hover:text-foreground transition-colors shrink-0 font-medium">
        <span>{isCurrentlyOpen ? "Viewing in workspace" : "Open in workspace"}</span>
        <ExternalLinkIcon className="size-3.5" />
      </div>
    </button>
  );
}
