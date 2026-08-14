"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi } from "@/features/billing/api/billing.api";
import { useTier } from "@/hooks/useTier";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckIcon, CreditCardIcon, AlertTriangleIcon, ExternalLinkIcon, SparklesIcon, ZapIcon } from "lucide-react";

export default function BillingPage() {
  const { tier } = useTier();

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
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "Failed to start Stripe checkout session.");
    }
  };

  const handleManageBilling = async () => {
    try {
      const res = await billingApi.createPortalSession();
      if (res.portal_url) {
        window.location.href = res.portal_url;
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "No active Stripe customer profile found.");
    }
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-8 font-sans p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight mb-1">Billing & Subscription Tier</h1>
        <p className="text-xs text-muted-foreground">Manage your SaaS chatbot tier, daily message limits, and billing preferences.</p>
      </div>

      {/* Current Subscription Box */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-border/40 pb-3">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <CreditCardIcon className="size-4 text-muted-foreground" /> Current Subscription Overview
          </h2>
          <Button variant="outline" size="sm" onClick={handleManageBilling} className="text-xs">
            Manage Billing <ExternalLinkIcon className="size-3 ml-1" />
          </Button>
        </div>

        {isSubLoading ? (
          <div className="py-2 text-xs text-muted-foreground font-mono animate-pulse">Loading subscription status...</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground block mb-1">Active Tier</span>
              <Badge variant="outline" className="font-mono text-xs px-2.5 py-0.5 border-primary/40 text-primary bg-primary/10">
                {tier}
              </Badge>
            </div>
            <div>
              <span className="text-muted-foreground block mb-1">Daily Limit</span>
              <span className="font-semibold text-foreground font-mono">
                {tier === "ADMIN" || tier === "ENTERPRISE" ? "Unlimited" : tier === "PRO" ? "250 msgs / day" : tier === "STARTER" ? "50 msgs / day" : "15 msgs / day"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block mb-1">Current Period End</span>
              <span className="font-mono text-foreground">
                {subData?.current_period_end
                  ? new Date(subData.current_period_end).toLocaleDateString()
                  : "N/A"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground block mb-1">Renewal Policy</span>
              <span className="font-mono text-foreground">
                {subData?.cancel_at_period_end ? (
                  <span className="text-amber-500 font-semibold flex items-center gap-1">
                    <AlertTriangleIcon className="size-3" /> Cancels at period end
                  </span>
                ) : (
                  "Auto-renews monthly"
                )}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Upgrade Options Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Starter Plan */}
        <div className="border border-border/60 p-6 rounded-2xl bg-card flex flex-col justify-between shadow-xs">
          <div>
            <h3 className="font-bold text-base mb-1 font-mono">Starter</h3>
            <p className="text-2xl font-extrabold mb-4 font-mono">$19 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 50 AI messages per day</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Gemini 3.7 Flash & GPT-4o-mini</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Standard Response Speed</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Chat Session History & Export</li>
            </ul>
          </div>
          <Button
            onClick={() => handleUpgrade("STARTER")}
            disabled={tier === "STARTER"}
            className="w-full text-xs font-medium"
          >
            {tier === "STARTER" ? "Current Plan" : "Upgrade to Starter"}
          </Button>
        </div>

        {/* Pro Plan */}
        <div className="border border-primary/60 p-6 rounded-2xl bg-card flex flex-col justify-between relative shadow-sm">
          <Badge className="absolute -top-3 right-4 bg-primary text-primary-foreground text-[10px] px-2 py-0.5 font-mono font-bold">
            MOST POPULAR
          </Badge>
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <SparklesIcon className="size-4 text-primary" />
              <h3 className="font-bold text-base font-mono">Pro</h3>
            </div>
            <p className="text-2xl font-extrabold mb-4 font-mono">$49 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 250 AI messages per day</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Priority High-Speed Inference</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Advanced Reasoning & Code Intelligence</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Extended Context Window</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Priority Support</li>
            </ul>
          </div>
          <Button
            onClick={() => handleUpgrade("PRO")}
            disabled={tier === "PRO"}
            className="w-full text-xs font-medium bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            {tier === "PRO" ? "Current Plan" : "Upgrade to Pro"}
          </Button>
        </div>

        {/* Enterprise Plan */}
        <div className="border border-border/60 p-6 rounded-2xl bg-card flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <ZapIcon className="size-4 text-amber-500" />
              <h3 className="font-bold text-base font-mono">Enterprise</h3>
            </div>
            <p className="text-2xl font-extrabold mb-4 font-mono">$199 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2.5 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Unlimited AI messages per day</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Dedicated High-Throughput Processing</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Custom Domain & Multi-User Seats</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Dedicated 24/7 SLA Support</li>
            </ul>
          </div>
          <Button
            onClick={() => handleUpgrade("ENTERPRISE")}
            disabled={tier === "ENTERPRISE"}
            variant="outline"
            className="w-full text-xs font-medium"
          >
            {tier === "ENTERPRISE" ? "Current Plan" : "Upgrade to Enterprise"}
          </Button>
        </div>
      </div>
    </div>
  );
}
