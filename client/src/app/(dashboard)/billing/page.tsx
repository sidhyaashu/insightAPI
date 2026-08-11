"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi } from "@/features/billing/api/billing.api";
import apiClient from "@/lib/api-client";
import { useTier } from "@/hooks/useTier";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckIcon, CreditCardIcon, AlertTriangleIcon } from "lucide-react";

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
    queryFn: async () => {
      try {
        const res = await apiClient.get("/payments/plans");
        return res.data;
      } catch {
        return {
          STARTER: "price_starter_placeholder",
          PRO: "price_pro_placeholder",
          ENTERPRISE: "price_enterprise_placeholder",
        };
      }
    },
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

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-8 font-sans">
      <div>
        <h1 className="text-xl font-bold tracking-tight mb-1">Billing & Subscription Tier</h1>
        <p className="text-xs text-muted-foreground">Manage active plan tier, usage quotas, and Stripe billing preferences.</p>
      </div>

      {/* Current Subscription Box */}
      <div className="border border-border/60 p-6 rounded-xl bg-card shadow-xs space-y-4">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 border-b border-border/40 pb-2">
          <CreditCardIcon className="size-4 text-muted-foreground" /> Current Subscription Overview
        </h2>
        {isSubLoading ? (
          <div className="py-2 text-xs text-muted-foreground font-mono animate-pulse">Loading subscription status...</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground block mb-1">Active Tier</span>
              <Badge variant="outline" className="font-mono text-xs px-2.5 py-0.5">
                {tier}
              </Badge>
            </div>
            <div>
              <span className="text-muted-foreground block mb-1">Subscription Status</span>
              <span className="font-semibold text-foreground capitalize font-mono">{subData?.status || "Free Plan"}</span>
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
        <div className="border border-border/60 p-6 rounded-xl bg-card flex flex-col justify-between shadow-xs">
          <div>
            <h3 className="font-bold text-base mb-1 font-mono">Starter</h3>
            <p className="text-2xl font-extrabold mb-4 font-mono">$29 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 20 crawls per day</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 50 pages per crawl</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> OpenAPI 3.1 & Postman v2.1 Export</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> AI Workspace Access</li>
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
        <div className="border border-primary/60 p-6 rounded-xl bg-card flex flex-col justify-between relative shadow-sm">
          <Badge className="absolute -top-3 right-4 bg-primary text-primary-foreground text-[10px] px-2 py-0.5 font-mono font-bold">
            RECOMMENDED
          </Badge>
          <div>
            <h3 className="font-bold text-base mb-1 font-mono">Pro</h3>
            <p className="text-2xl font-extrabold mb-4 font-mono">$99 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 100 crawls per day</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 200 pages per crawl</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 3 Parallel Agent Workers</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> GPT-4o Vision Fallback</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Priority Crawl Queue</li>
            </ul>
          </div>
          <Button
            onClick={() => handleUpgrade("PRO")}
            disabled={tier === "PRO"}
            className="w-full text-xs font-medium"
          >
            {tier === "PRO" ? "Current Plan" : "Upgrade to Pro"}
          </Button>
        </div>

        {/* Enterprise Plan */}
        <div className="border border-border/60 p-6 rounded-xl bg-card flex flex-col justify-between shadow-xs">
          <div>
            <h3 className="font-bold text-base mb-1 font-mono">Enterprise</h3>
            <p className="text-2xl font-extrabold mb-4 font-mono">$499 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Unlimited Crawls & Pages</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> On-Premises Docker Deployment</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> 10 Parallel Agent Workers</li>
              <li className="flex items-center gap-1.5"><CheckIcon className="size-3.5 text-emerald-500" /> Dedicated SLA & Support</li>
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
