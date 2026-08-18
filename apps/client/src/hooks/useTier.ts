"use client";

import { useAppSelector } from "@/store";

const TIER_HIERARCHY: Record<string, number> = {
  FREE: 0,
  STARTER: 1,
  PRO: 2,
  ENTERPRISE: 3,
  ADMIN: 99,
};

export function useTier() {
  const user = useAppSelector((state) => state.auth.user);
  const tier = user?.tier ?? "FREE";
  const tierLevel = TIER_HIERARCHY[tier] ?? 0;

  const hasTierAccess = (requiredTier: "FREE" | "STARTER" | "PRO" | "ENTERPRISE" | "ADMIN"): boolean => {
    const requiredLevel = TIER_HIERARCHY[requiredTier] ?? 0;
    return tierLevel >= requiredLevel;
  };

  return {
    tier,
    tierLevel,
    isFree: tier === "FREE",
    isStarter: tier === "STARTER",
    isPro: tier === "PRO",
    isEnterprise: tier === "ENTERPRISE",
    isAdmin: tier === "ADMIN" || user?.role === "admin",
    hasTierAccess,
  };
}
