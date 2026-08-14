"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { SlidersIcon, ShieldCheckIcon, BotIcon, GlobeIcon, AlertTriangleIcon, ExternalLinkIcon, CheckCircle2Icon } from "lucide-react";
import { domainsApi } from "@/features/domains/api/domains.api";
import { authProfilesApi } from "@/features/auth-profiles/api/authProfiles.api";
import type { AuthProfile } from "@/lib/api-client/types";
import { KeyRoundIcon } from "lucide-react";

export interface CrawlSettings {
  targetUrl: string;
  maxPages: number;
  jsRendering: boolean;
  stealthMode: boolean;
  requireReview: boolean;
  model: string;
  authHeader: string;
  authProfileId?: string;
  tosAccepted: boolean;
}

interface CrawlSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (settings: CrawlSettings) => void;
  initialSettings?: Partial<CrawlSettings>;
}

export function CrawlSettingsModal({
  open,
  onOpenChange,
  onSave,
  initialSettings,
}: CrawlSettingsModalProps) {
  const [settings, setSettings] = useState<CrawlSettings>({
    targetUrl: initialSettings?.targetUrl || "",
    maxPages: initialSettings?.maxPages || 15,
    jsRendering: initialSettings?.jsRendering ?? true,
    stealthMode: initialSettings?.stealthMode ?? true,
    requireReview: initialSettings?.requireReview ?? true,
    model: initialSettings?.model || "gpt-4o-mini",
    authHeader: initialSettings?.authHeader || "",
    authProfileId: initialSettings?.authProfileId || "none",
    tosAccepted: initialSettings?.tosAccepted ?? false,
  });

  const [domainVerified, setDomainVerified] = useState<boolean | null>(null);
  const [checkingDomain, setCheckingDomain] = useState(false);
  const [authProfiles, setAuthProfiles] = useState<AuthProfile[]>([]);

  // Load auth profiles on mount
  useEffect(() => {
    authProfilesApi.listProfiles().then(setAuthProfiles).catch(() => setAuthProfiles([]));
  }, []);

  // Check domain verification status on targetUrl change
  useEffect(() => {
    const rawUrl = settings.targetUrl.trim();
    if (!rawUrl) {
      setDomainVerified(null);
      return;
    }

    const timer = setTimeout(async () => {
      setCheckingDomain(true);
      try {
        const res = await domainsApi.checkStatus(rawUrl);
        setDomainVerified(res.is_verified);
      } catch {
        setDomainVerified(false);
      } finally {
        setCheckingDomain(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [settings.targetUrl]);

  const canSubmit = !settings.targetUrl.trim() || domainVerified === true || settings.tosAccepted;

  const handleSave = () => {
    onSave(settings);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-6 rounded-2xl shadow-2xl bg-card text-card-foreground border border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-bold">
            <SlidersIcon className="size-5 text-primary" />
            Crawl & AI Execution Settings
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Configure agentic crawler behavior, domain verification, and model selection.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          {/* Target Web App URL & Verification Badge */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold flex items-center gap-1.5">
                <GlobeIcon className="size-3.5 text-primary" />
                Target Web Application URL
              </Label>
              {checkingDomain ? (
                <span className="text-[10px] text-muted-foreground font-mono animate-pulse">Checking domain…</span>
              ) : domainVerified === true ? (
                <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500 bg-emerald-500/10 gap-1 px-1.5 py-0">
                  <CheckCircle2Icon className="size-2.5" /> Verified Target
                </Badge>
              ) : settings.targetUrl.trim() ? (
                <Badge variant="outline" className="text-[10px] font-mono border-amber-500/40 text-amber-500 bg-amber-500/10 gap-1 px-1.5 py-0">
                  <AlertTriangleIcon className="size-2.5" /> Unverified Target
                </Badge>
              ) : null}
            </div>
            <Input
              placeholder="https://api.example.com"
              value={settings.targetUrl}
              onChange={(e) => setSettings({ ...settings, targetUrl: e.target.value })}
              className="text-xs font-mono"
            />
          </div>

          {/* Unverified Domain ToS Acceptance Notice */}
          {settings.targetUrl.trim() && domainVerified === false && (
            <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2">
              <div className="flex items-start gap-2">
                <input
                  type="checkbox"
                  id="tos-accepted-checkbox"
                  checked={settings.tosAccepted}
                  onChange={(e) => setSettings({ ...settings, tosAccepted: e.target.checked })}
                  className="mt-0.5 size-3.5 rounded border-border accent-primary cursor-pointer"
                />
                <label htmlFor="tos-accepted-checkbox" className="text-[11px] text-foreground leading-tight cursor-pointer">
                  I confirm that I have explicit authorization to crawl this target and accept the{" "}
                  <Link href="/tos" target="_blank" className="text-primary underline font-semibold inline-flex items-center gap-0.5">
                    Acceptable Use Policy & ToS <ExternalLinkIcon className="size-2.5 ml-0.5" />
                  </Link>.
                </label>
              </div>
              <p className="text-[10px] text-muted-foreground pl-5.5">
                Tip: <Link href="/domains" className="text-primary underline">Verify domain ownership</Link> to permanently exempt this host from per-session confirmations.
              </p>
            </div>
          )}

          {/* AI Model Selection */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold flex items-center gap-1.5">
              <BotIcon className="size-3.5 text-purple-400" />
              AI Intelligence Model
            </Label>
            <Select
              value={settings.model}
              onValueChange={(val) => setSettings({ ...settings, model: val || "gpt-4o-mini" })}
            >
              <SelectTrigger className="text-xs">
                <SelectValue placeholder="Select Model" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gpt-4o-mini" className="text-xs font-mono">
                  GPT-4o-mini (Fast & Recommended)
                </SelectItem>
                <SelectItem value="gpt-4o" className="text-xs font-mono">
                  GPT-4o (High Reasoning Depth)
                </SelectItem>
                <SelectItem value="ollama-local" className="text-xs font-mono">
                  Ollama / Local LLM Endpoint
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Max Crawl Pages */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Max Pages to Crawl</Label>
            <Input
              type="number"
              min={1}
              max={100}
              value={settings.maxPages}
              onChange={(e) => setSettings({ ...settings, maxPages: parseInt(e.target.value) || 10 })}
              className="text-xs font-mono"
            />
          </div>

          {/* Stealth & JS Rendering Toggles */}
          <div className="pt-2 border-t space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Playwright JS Rendering</p>
                <p className="text-[11px] text-muted-foreground">Executes Single Page Apps (React/Vue)</p>
              </div>
              <Switch
                checked={settings.jsRendering}
                onCheckedChange={(val) => setSettings({ ...settings, jsRendering: val })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Anti-Bot Stealth Engine</p>
                <p className="text-[11px] text-muted-foreground">Spoofs WebGL signatures & overrides concurrency</p>
              </div>
              <Switch
                checked={settings.stealthMode}
                onCheckedChange={(val) => setSettings({ ...settings, stealthMode: val })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Human-in-the-Loop Review Gate</p>
                <p className="text-[11px] text-muted-foreground">Pause for schema review before final export</p>
              </div>
              <Switch
                checked={settings.requireReview}
                onCheckedChange={(val) => setSettings({ ...settings, requireReview: val })}
              />
            </div>
          </div>

          {/* Automated Auth Profile Selection */}
          <div className="space-y-1.5 pt-2 border-t">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold flex items-center gap-1.5">
                <KeyRoundIcon className="size-3.5 text-amber-400" />
                Target Login Profile (Auto-Authentication)
              </Label>
              <Link href="/auth-profiles" className="text-[10px] text-primary underline hover:opacity-80">
                Manage Profiles
              </Link>
            </div>
            <Select
              value={settings.authProfileId || "none"}
              onValueChange={(val) => setSettings({ ...settings, authProfileId: (!val || val === "none") ? undefined : val })}
            >
              <SelectTrigger className="text-xs font-mono">
                <SelectValue placeholder="Select login profile" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none" className="text-xs font-mono">
                  None (Public / Unauthenticated Crawl)
                </SelectItem>
                {authProfiles.map((p) => (
                  <SelectItem key={p.id} value={p.id} className="text-xs font-mono">
                    [{p.auth_type.toUpperCase()}] {p.name} ({p.target_domain})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Auth Header */}
          <div className="space-y-1.5 pt-2 border-t">
            <Label className="text-xs font-semibold flex items-center gap-1.5">
              <ShieldCheckIcon className="size-3.5 text-emerald-400" />
              Custom Authorization Header (Optional)
            </Label>
            <Input
              placeholder="Bearer eyJhbGciOi..."
              value={settings.authHeader}
              onChange={(e) => setSettings({ ...settings, authHeader: e.target.value })}
              className="text-xs font-mono"
            />
          </div>
        </div>

        <DialogFooter className="pt-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!canSubmit}
            className="bg-primary text-primary-foreground"
          >
            Save & Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

