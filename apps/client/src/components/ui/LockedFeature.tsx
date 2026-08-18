"use client";

import React from "react";
import Link from "next/link";
import { useTier } from "@/hooks/useTier";
import { Tooltip } from "@/components/ui/tooltip";

interface LockedFeatureProps {
  requiredTier: "FREE" | "STARTER" | "PRO" | "ENTERPRISE" | "ADMIN";
  children: React.ReactNode;
  featureName?: string;
  className?: string;
}

export function LockedFeature({
  requiredTier,
  children,
  featureName = "Feature",
  className = "",
}: LockedFeatureProps) {
  const { hasTierAccess } = useTier();
  const unlocked = hasTierAccess(requiredTier);

  if (unlocked) {
    return <>{children}</>;
  }

  return (
    <div className={`relative group ${className}`}>
      {/* Grayed-out & disabled content */}
      <div className="opacity-40 grayscale pointer-events-none select-none filter blur-[0.3px]">
        {children}
      </div>

      {/* Lock Overlay Banner */}
      <div className="absolute inset-0 flex items-center justify-center bg-background/40 backdrop-blur-[1px] rounded-lg border border-dashed border-amber-500/40 p-2 z-10">
        <Tooltip
          side="top"
          content={
            <div className="flex flex-col gap-1 text-center">
              <span className="font-semibold text-amber-500">🔒 {featureName} Locked</span>
              <span className="text-[11px] text-muted-foreground">
                Requires <strong className="text-foreground">{requiredTier}</strong> tier or higher.
              </span>
              <span className="text-[10px] text-primary underline mt-1">Click to Upgrade Plan &rarr;</span>
            </div>
          }
        >
          <Link
            href="/billing"
            className="flex items-center gap-1.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 px-3 py-1.5 rounded-full text-xs font-semibold hover:bg-amber-500/20 transition shadow-sm"
          >
            <span>🔒</span>
            <span>Unlock {featureName} ({requiredTier}+)</span>
          </Link>
        </Tooltip>
      </div>
    </div>
  );
}
