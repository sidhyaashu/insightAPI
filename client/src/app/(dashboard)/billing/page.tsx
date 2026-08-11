"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi } from "@/features/billing/api/billing.api";
import { useTier } from "@/hooks/useTier";
import env from "@/lib/env";

export default function BillingPage() {
  const { tier } = useTier();

  const { data: subData, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => billingApi.getSubscription(),
  });

  const handleUpgrade = async (priceId: string) => {
    try {
      const res = await billingApi.createCheckoutSession(priceId);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || "Failed to start checkout");
    }
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight mb-1">Billing & Subscriptions</h1>
        <p className="text-sm text-muted-foreground">Manage your plan tier and billing preferences</p>
      </div>

      {/* Current Subscription Box */}
      <div className="border border-border p-6 rounded-xl bg-card shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Current Plan Overview</h2>
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading subscription...</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-xs text-muted-foreground block">Active Tier</span>
              <span className="font-bold text-lg">{tier}</span>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Subscription Status</span>
              <span className="font-semibold capitalize">{subData?.status || "Free Account"}</span>
            </div>
            <div>
              <span className="text-xs text-muted-foreground block">Current Period End</span>
              <span>
                {subData?.current_period_end
                  ? new Date(subData.current_period_end).toLocaleDateString()
                  : "N/A"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Upgrade Options Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Starter Plan */}
        <div className="border border-border p-6 rounded-xl bg-card flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg mb-1">Starter</h3>
            <p className="text-3xl font-extrabold mb-4">$29 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li>✓ 20 crawls per day</li>
              <li>✓ 50 pages per crawl</li>
              <li>✓ OpenAPI & Postman Exporters</li>
              <li>✓ AI Chatbot (50 queries/day)</li>
            </ul>
          </div>
          <button
            onClick={() => handleUpgrade("price_starter_placeholder")}
            disabled={tier === "STARTER"}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {tier === "STARTER" ? "Current Plan" : "Upgrade to Starter"}
          </button>
        </div>

        {/* Pro Plan */}
        <div className="border-2 border-primary p-6 rounded-xl bg-card flex flex-col justify-between relative shadow-md">
          <span className="absolute -top-3 right-4 bg-primary text-primary-foreground text-[10px] px-2 py-0.5 rounded-full font-bold">
            RECOMMENDED
          </span>
          <div>
            <h3 className="font-bold text-lg mb-1">Pro</h3>
            <p className="text-3xl font-extrabold mb-4">$99 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li>✓ 100 crawls per day</li>
              <li>✓ 200 pages per crawl</li>
              <li>✓ 3 Parallel Agent Workers</li>
              <li>✓ Unlimited AI Chatbot</li>
              <li>✓ GPT-4o Vision Fallback</li>
              <li>✓ Priority Crawl Queue</li>
            </ul>
          </div>
          <button
            onClick={() => handleUpgrade("price_pro_placeholder")}
            disabled={tier === "PRO"}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:opacity-90 disabled:opacity-50"
          >
            {tier === "PRO" ? "Current Plan" : "Upgrade to Pro"}
          </button>
        </div>

        {/* Enterprise Plan */}
        <div className="border border-border p-6 rounded-xl bg-card flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-lg mb-1">Enterprise</h3>
            <p className="text-3xl font-extrabold mb-4">$499 <span className="text-xs font-normal text-muted-foreground">/ month</span></p>
            <ul className="text-xs flex flex-col gap-2 text-muted-foreground mb-6">
              <li>✓ Unlimited Crawls & Pages</li>
              <li>✓ Self-Hosted Docker License</li>
              <li>✓ 10 Parallel Agent Workers</li>
              <li>✓ Dedicated Support Channel</li>
            </ul>
          </div>
          <button
            onClick={() => handleUpgrade("price_enterprise_placeholder")}
            disabled={tier === "ENTERPRISE"}
            className="w-full py-2.5 border border-input bg-background font-medium text-sm rounded-lg hover:bg-accent disabled:opacity-50"
          >
            {tier === "ENTERPRISE" ? "Current Plan" : "Contact Sales"}
          </button>
        </div>
      </div>
    </div>
  );
}
