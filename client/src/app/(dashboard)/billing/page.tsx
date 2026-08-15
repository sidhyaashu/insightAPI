"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { billingApi } from "@/features/billing/api/billing.api";
import { authApi } from "@/features/auth/api/auth.api";
import { useTier } from "@/hooks/useTier";
import { useAppSelector, useAppDispatch } from "@/store";
import { updateUser } from "@/features/auth/store/authSlice";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  CheckIcon,
  CreditCardIcon,
  AlertTriangleIcon,
  ExternalLinkIcon,
  SparklesIcon,
  ZapIcon,
  ShieldCheckIcon,
  CoinsIcon,
} from "lucide-react";

export default function BillingPage() {
  const { tier } = useTier();
  const dispatch = useAppDispatch();
  const authUser = useAppSelector((state) => state.auth.user);
  const queryClient = useQueryClient();

  const [allowOverage, setAllowOverage] = useState<boolean>(authUser?.allow_overage ?? false);
  const [updatingOverage, setUpdatingOverage] = useState<boolean>(false);

  // Sync allowOverage with authUser state
  useEffect(() => {
    if (authUser?.allow_overage !== undefined) {
      setAllowOverage(authUser.allow_overage);
    }
  }, [authUser?.allow_overage]);

  // Fetch subscription info
  const { data: subData, isLoading: isSubLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => billingApi.getSubscription(),
  });

  // Fetch backend Stripe plan price IDs dynamically
  const { data: plansData } = useQuery({
    queryKey: ["payment-plans"],
    queryFn: () => billingApi.getPlans(),
  });

  const handleToggleOverage = async (checked: boolean) => {
    setAllowOverage(checked);
    setUpdatingOverage(true);
    try {
      const res = await billingApi.updateOveragePreference(checked);
      dispatch(updateUser({ allow_overage: res.allow_overage }));
      toast.success(
        checked
          ? "Pay-per-crawl overage enabled ($1.50/crawl beyond plan quota)."
          : "Pay-per-crawl overage disabled. Hard crawl limit active."
      );
    } catch (err: unknown) {
      setAllowOverage(!checked);
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to update overage preference.";
      toast.error(msg);
    } finally {
      setUpdatingOverage(false);
    }
  };

  const handleUpgrade = async (tierName: string) => {
    const priceId = plansData?.[tierName];
    if (!priceId) {
      toast.error(`Payment gateway for ${tierName} plan is currently being configured.`);
      return;
    }

    try {
      const res = await billingApi.createCheckoutSession(priceId);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to start Stripe checkout session.";
      toast.error(msg);
    }
  };

  const handleManageBilling = async () => {
    try {
      const res = await billingApi.createPortalSession();
      if (res.portal_url) {
        window.location.href = res.portal_url;
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "No active Stripe customer profile found.";
      toast.error(msg);
    }
  };

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8 font-sans p-4 sm:p-8 pb-28">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground mb-1">
          Subscription Tiers & Metered Billing
        </h1>
        <p className="text-xs text-muted-foreground">
          Manage your SaaS plan quota, pay-per-crawl overage settings, and automated Stripe billing cycle.
        </p>
      </div>

      {/* Current Subscription Box */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs space-y-5">
        <div className="flex items-center justify-between border-b border-border/40 pb-3.5 flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20">
              <CreditCardIcon className="size-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-foreground">Current Active Subscription</h2>
              <p className="text-[11px] text-muted-foreground">Managed via Stripe Customer Portal</p>
            </div>
          </div>

          <Button variant="outline" size="sm" onClick={handleManageBilling} className="text-xs gap-1.5 h-8">
            Manage Stripe Billing <ExternalLinkIcon className="size-3.5" />
          </Button>
        </div>

        {isSubLoading ? (
          <div className="py-4 text-xs text-muted-foreground font-mono animate-pulse">
            Loading subscription status...
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="p-3.5 rounded-xl bg-muted/20 border border-border/40">
              <span className="text-muted-foreground block mb-1 text-[11px] font-mono">Active Tier</span>
              <Badge
                variant="outline"
                className="font-mono text-xs px-2.5 py-0.5 border-primary/40 text-primary bg-primary/10 font-bold"
              >
                {tier}
              </Badge>
            </div>
            <div className="p-3.5 rounded-xl bg-muted/20 border border-border/40">
              <span className="text-muted-foreground block mb-1 text-[11px] font-mono">Daily Crawl Quota</span>
              <span className="font-extrabold text-foreground font-mono text-sm">
                {tier === "ADMIN" || tier === "ENTERPRISE"
                  ? "Unlimited"
                  : tier === "PRO"
                  ? "100 crawls / day"
                  : tier === "STARTER"
                  ? "20 crawls / day"
                  : "1 crawl / day"}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-muted/20 border border-border/40">
              <span className="text-muted-foreground block mb-1 text-[11px] font-mono">Billing Cycle End</span>
              <span className="font-mono text-foreground font-semibold">
                {subData?.current_period_end
                  ? new Date(subData.current_period_end).toLocaleDateString()
                  : "N/A (Free Tier)"}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-muted/20 border border-border/40">
              <span className="text-muted-foreground block mb-1 text-[11px] font-mono">Renewal Policy</span>
              <span className="font-mono text-foreground">
                {subData?.cancel_at_period_end ? (
                  <span className="text-amber-500 font-semibold flex items-center gap-1">
                    <AlertTriangleIcon className="size-3" /> Cancels at period end
                  </span>
                ) : (
                  <span className="text-emerald-500 font-semibold flex items-center gap-1">
                    <CheckIcon className="size-3" /> Auto-renews monthly
                  </span>
                )}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Pay-Per-Crawl Overage Protection Card */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-border/40 pb-3 flex-wrap gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <CoinsIcon className="size-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-foreground">Pay-Per-Crawl Overage Protection</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Automatically bill $1.50 per additional crawl when your daily plan limit is reached.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-muted-foreground font-medium">
              {allowOverage ? "Overage Allowed" : "Hard Limit (Off)"}
            </span>
            <Switch
              checked={allowOverage}
              onCheckedChange={handleToggleOverage}
              disabled={updatingOverage}
            />
          </div>
        </div>

        <div className="text-xs text-muted-foreground space-y-1.5 bg-muted/20 p-4 rounded-xl border border-border/40 leading-relaxed">
          <p className="font-semibold text-foreground flex items-center gap-1.5">
            <ShieldCheckIcon className="size-4 text-emerald-400" />
            Zero-surprise-bills safeguard active
          </p>
          <p>
            When enabled, API crawl requests that exceed your daily tier quota bypass the 429 rate-limit
            block and create a $1.50 metered usage item on your next Stripe invoice. When disabled, crawls
            stop strictly at your plan limit.
          </p>
        </div>
      </div>

      {/* Upgrade Options Grid */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-foreground">Available Plans & Subscription Tiers</h2>
          <p className="text-xs text-muted-foreground">Select the right compute allocation and agent capacity for your team.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Pay-as-you-go Plan */}
          <div className="border border-border/60 p-6 rounded-2xl bg-card flex flex-col justify-between shadow-xs hover:border-border/80 transition-all">
            <div>
              <h3 className="font-bold text-base mb-1 font-mono text-foreground">Pay-as-you-go</h3>
              <p className="text-2xl font-extrabold mb-4 font-mono text-foreground">
                $1.50 <span className="text-xs font-normal text-muted-foreground">/ crawl</span>
              </p>
              <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Metered billing per crawl
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> No monthly commitment
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> OpenAPI 3.1 & Postman
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Full Safety Guardrails
                </li>
              </ul>
            </div>
            <Button
              variant={allowOverage ? "secondary" : "outline"}
              onClick={() => handleToggleOverage(!allowOverage)}
              className="w-full text-xs font-semibold h-9"
            >
              {allowOverage ? "Enabled (Active)" : "Enable Pay-as-you-go"}
            </Button>
          </div>

          {/* Starter Plan */}
          <div className="border border-border/60 p-6 rounded-2xl bg-card flex flex-col justify-between shadow-xs hover:border-border/80 transition-all">
            <div>
              <h3 className="font-bold text-base mb-1 font-mono text-foreground">Starter</h3>
              <p className="text-2xl font-extrabold mb-4 font-mono text-foreground">
                $29 <span className="text-xs font-normal text-muted-foreground">/ month</span>
              </p>
              <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 20 crawls per day
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Max 50 pages / domain
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 50 AI queries per day
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Standard Email Support
                </li>
              </ul>
            </div>
            <Button
              onClick={() => handleUpgrade("STARTER")}
              disabled={tier === "STARTER"}
              className="w-full text-xs font-semibold h-9"
            >
              {tier === "STARTER" ? "Current Plan" : "Upgrade to Starter"}
            </Button>
          </div>

          {/* Pro Plan */}
          <div className="border-2 border-primary p-6 rounded-2xl bg-card flex flex-col justify-between relative shadow-md">
            <Badge className="absolute -top-3 right-4 bg-primary text-primary-foreground text-[10px] px-2.5 py-0.5 font-mono font-bold shadow-xs">
              MOST POPULAR
            </Badge>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <SparklesIcon className="size-4 text-primary" />
                <h3 className="font-bold text-base font-mono text-foreground">Pro</h3>
              </div>
              <p className="text-2xl font-extrabold mb-4 font-mono text-foreground">
                $99 <span className="text-xs font-normal text-muted-foreground">/ month</span>
              </p>
              <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 100 crawls per day
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 3 Parallel Sub-Agents
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Unlimited AI Queries
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> API Drift Detection
                </li>
              </ul>
            </div>
            <Button
              onClick={() => handleUpgrade("PRO")}
              disabled={tier === "PRO"}
              className="w-full text-xs font-semibold h-9 bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs"
            >
              {tier === "PRO" ? "Current Plan" : "Upgrade to Pro"}
            </Button>
          </div>

          {/* Enterprise Plan */}
          <div className="border border-border/60 p-6 rounded-2xl bg-card flex flex-col justify-between shadow-xs hover:border-border/80 transition-all">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <ZapIcon className="size-4 text-amber-500" />
                <h3 className="font-bold text-base font-mono text-foreground">Enterprise</h3>
              </div>
              <p className="text-2xl font-extrabold mb-4 font-mono text-foreground">
                $499 <span className="text-xs font-normal text-muted-foreground">/ month</span>
              </p>
              <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Unlimited crawls & pages
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 10 Parallel Exploration Agents
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> Self-Hosted Docker deployment
                </li>
                <li className="flex items-center gap-2">
                  <CheckIcon className="size-3.5 text-emerald-500 shrink-0" /> 24/7 SLA Support
                </li>
              </ul>
            </div>
            <Button
              onClick={() => handleUpgrade("ENTERPRISE")}
              disabled={tier === "ENTERPRISE"}
              variant="outline"
              className="w-full text-xs font-semibold h-9"
            >
              {tier === "ENTERPRISE" ? "Current Plan" : "Contact Enterprise"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

