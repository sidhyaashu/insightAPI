"use client";

import { useAppSelector } from "@/store";
import Link from "next/link";
import { UserIcon, ShieldCheckIcon, CreditCardIcon, SparklesIcon, MailIcon, CheckCircle2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function SettingsPage() {
  const user = useAppSelector((state) => state.auth.user);

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6 font-sans p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight mb-1">Account & Preferences</h1>
        <p className="text-xs text-muted-foreground">
          Manage your personal profile, active subscription plan, and system preferences.
        </p>
      </div>

      {/* User Profile Information */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-border/40 pb-3">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <UserIcon className="size-4 text-muted-foreground" /> Personal Profile
          </h2>
          <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500 bg-emerald-500/10">
            <CheckCircle2Icon className="size-3 mr-1" /> Active
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-muted-foreground mb-1 font-medium">Full Name</label>
            <Input readOnly value={user?.name || "Asutosh Sidhya"} className="font-medium bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1 font-medium">Email Address</label>
            <Input readOnly value={user?.email || "sidhyaasutosh@gmail.com"} className="font-medium bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1 font-medium">Authentication Method</label>
            <Input readOnly value={user?.oauth_provider ? `${user.oauth_provider.toUpperCase()} OAuth` : "Email & Password"} className="font-medium bg-muted/30" />
          </div>
          <div>
            <label className="block text-muted-foreground mb-1 font-medium">Account ID</label>
            <Input readOnly value={user?.id || "N/A"} className="font-mono text-xs bg-muted/30 text-muted-foreground" />
          </div>
        </div>
      </div>

      {/* Active Subscription & Plan Quota */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-border/40 pb-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <CreditCardIcon className="size-4 text-muted-foreground" /> Subscription Plan
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Your active subscription determines your daily AI chatbot message limit.
            </p>
          </div>
          <Badge variant="outline" className="font-mono text-xs px-2.5 py-0.5 border-primary/40 text-primary bg-primary/10">
            {user?.tier || "FREE"} Plan
          </Badge>
        </div>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl border border-border/40 bg-muted/20">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <SparklesIcon className="size-3.5 text-primary" />
              {user?.tier === "ADMIN" ? "Admin Full Access" : user?.tier === "ENTERPRISE" ? "Enterprise Plan (Unlimited AI Messages)" : user?.tier === "PRO" ? "Pro Plan (250 Messages/day)" : "Free Plan (15 Messages/day)"}
            </span>
            <p className="text-xs text-muted-foreground">
              {user?.tier === "ADMIN" || user?.tier === "ENTERPRISE"
                ? "You have unrestricted access to all AI intelligence features."
                : "Upgrade your tier to unlock higher daily messaging quotas and faster inference speed."}
            </p>
          </div>

          <Link href="/billing">
            <Button size="sm" className="bg-primary text-primary-foreground font-medium text-xs shrink-0">
              Manage / Upgrade Plan
            </Button>
          </Link>
        </div>
      </div>

      {/* Appearance & Theme */}
      <div className="border border-border/60 p-6 rounded-2xl bg-card shadow-xs flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Theme & Appearance</h2>
          <p className="text-xs text-muted-foreground mt-0.5">Toggle between dark and light themes for your workspace.</p>
        </div>
        <ThemeToggle />
      </div>
    </div>
  );
}
