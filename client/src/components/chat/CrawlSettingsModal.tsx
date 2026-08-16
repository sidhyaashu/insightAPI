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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  SlidersIcon,
  ShieldCheckIcon,
  BotIcon,
  GlobeIcon,
  AlertTriangleIcon,
  ExternalLinkIcon,
  CheckCircle2Icon,
  KeyRoundIcon,
  Loader2Icon,
  PlayIcon,
  AlertCircleIcon,
  LayersIcon,
  CpuIcon,
  ShieldAlertIcon,
  EyeIcon,
} from "lucide-react";
import { domainsApi } from "@/features/domains/api/domains.api";
import { authProfilesApi } from "@/features/auth-profiles/api/authProfiles.api";
import type { AuthProfile } from "@/lib/api-client/types";

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
  onSave: (settings: CrawlSettings) => Promise<boolean | void> | void;
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
    model: initialSettings?.model || "gpt-4.1-mini",
    authHeader: initialSettings?.authHeader || "",
    authProfileId: initialSettings?.authProfileId || "none",
    tosAccepted: initialSettings?.tosAccepted ?? false,
  });

  const [domainVerified, setDomainVerified] = useState<boolean | null>(null);
  const [checkingDomain, setCheckingDomain] = useState(false);
  const [authProfiles, setAuthProfiles] = useState<AuthProfile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sync settings whenever modal opens or initialSettings change
  useEffect(() => {
    if (open) {
      setSettings({
        targetUrl: initialSettings?.targetUrl || "",
        maxPages: initialSettings?.maxPages || 15,
        jsRendering: initialSettings?.jsRendering ?? true,
        stealthMode: initialSettings?.stealthMode ?? true,
        requireReview: initialSettings?.requireReview ?? true,
        model: initialSettings?.model || "gpt-4.1-mini",
        authHeader: initialSettings?.authHeader || "",
        authProfileId: initialSettings?.authProfileId || "none",
        tosAccepted: initialSettings?.tosAccepted ?? false,
      });
      setErrorMsg(null);
      setIsSubmitting(false);
      authProfilesApi.listProfiles().then(setAuthProfiles).catch(() => setAuthProfiles([]));
    }
  }, [open, initialSettings]);

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

  const hasUrl = Boolean(settings.targetUrl.trim());
  const canSubmit = hasUrl && (domainVerified === true || settings.tosAccepted) && !isSubmitting;

  const handleSave = async () => {
    const trimmed = settings.targetUrl.trim();
    if (!trimmed) {
      setErrorMsg("Please enter a Target Web Application URL (e.g. https://example.com)");
      return;
    }

    const normalizedUrl = (trimmed.startsWith("http://") || trimmed.startsWith("https://"))
      ? trimmed
      : `https://${trimmed}`;

    const normalizedSettings = {
      ...settings,
      targetUrl: normalizedUrl,
    };

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await onSave(normalizedSettings);
      onOpenChange(false);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to launch autonomous crawl. Please verify your settings.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!isSubmitting) onOpenChange(v); }}>
      <DialogContent className="max-w-3xl max-h-[88vh] flex flex-col p-0 overflow-hidden rounded-2xl shadow-2xl bg-card text-card-foreground border border-border">
        {/* Fixed Header */}
        <DialogHeader className="p-5 pb-3.5 border-b border-border/60 bg-muted/20 shrink-0 text-left">
          <div className="flex items-center justify-between pr-6">
            <DialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold tracking-tight">
              <span className="p-1.5 rounded-lg bg-primary/10 text-primary">
                <SlidersIcon className="size-4.5" />
              </span>
              Crawl &amp; AI Execution Settings
            </DialogTitle>
            <Badge variant="outline" className="hidden sm:inline-flex text-[10px] font-mono border-primary/30 text-primary bg-primary/5">
              Playwright + LangGraph
            </Badge>
          </div>
          <DialogDescription className="text-xs text-muted-foreground mt-1">
            Configure agentic crawler behavior, authentication, domain compliance, and LLM reasoning models.
          </DialogDescription>
        </DialogHeader>

        {/* Scrollable Content Body with 2-Column Responsive Layout */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {errorMsg && (
            <div className="p-3 rounded-xl border border-destructive/40 bg-destructive/10 text-destructive text-xs flex items-start gap-2.5 animate-in fade-in">
              <AlertCircleIcon className="size-4 shrink-0 mt-0.5" />
              <span className="leading-snug">{errorMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4.5">
            {/* LEFT COLUMN: Target Configuration & Authentication */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground/90 uppercase tracking-wider pb-1 border-b border-border/40">
                <GlobeIcon className="size-3.5 text-primary" />
                <span>Target &amp; Identity</span>
              </div>

              {/* Target Web App URL & Verification Badge */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5">
                    Target Web Application URL <span className="text-destructive">*</span>
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
                  placeholder="https://api.example.com or https://app.example.com"
                  value={settings.targetUrl}
                  onChange={(e) => {
                    setSettings({ ...settings, targetUrl: e.target.value });
                    if (errorMsg) setErrorMsg(null);
                  }}
                  className="text-xs font-mono h-9 bg-background/80"
                />
              </div>

              {/* Unverified Domain ToS Acceptance Notice */}
              {settings.targetUrl.trim() && domainVerified === false && (
                <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2 animate-in fade-in">
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
                        Acceptable Use Policy &amp; ToS <ExternalLinkIcon className="size-2.5 ml-0.5" />
                      </Link>.
                    </label>
                  </div>
                  <p className="text-[10px] text-muted-foreground pl-5.5">
                    Tip: <Link href="/domains" className="text-primary underline">Verify domain ownership</Link> to permanently exempt this host from per-session confirmations.
                  </p>
                </div>
              )}

              {/* Automated Auth Profile Selection */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5">
                    <KeyRoundIcon className="size-3.5 text-amber-400" />
                    Target Login Profile (Auto-Auth)
                  </Label>
                  <Link href="/auth-profiles" className="text-[10px] text-primary underline hover:opacity-80 cursor-pointer">
                    Manage Profiles
                  </Link>
                </div>
                <Select
                  value={settings.authProfileId || "none"}
                  onValueChange={(val) => setSettings({ ...settings, authProfileId: (!val || val === "none") ? "none" : val })}
                >
                  <SelectTrigger className="w-full text-xs font-mono bg-background/80 border-border hover:bg-muted/40 cursor-pointer h-9">
                    <SelectValue placeholder="Select login profile" />
                  </SelectTrigger>
                  <SelectContent className="z-[100]">
                    <SelectItem value="none" className="text-xs font-mono cursor-pointer">
                      None (Public / Unauthenticated Crawl)
                    </SelectItem>
                    {authProfiles.map((p) => (
                      <SelectItem key={p.id} value={p.id} className="text-xs font-mono cursor-pointer">
                        [{p.auth_type.toUpperCase()}] {p.name} ({p.target_domain})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Custom Authorization Header */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold flex items-center gap-1.5">
                  <ShieldCheckIcon className="size-3.5 text-emerald-400" />
                  Custom Authorization Header (Optional)
                </Label>
                <Input
                  placeholder="Bearer eyJhbGciOi..."
                  value={settings.authHeader}
                  onChange={(e) => setSettings({ ...settings, authHeader: e.target.value })}
                  className="text-xs font-mono h-9 bg-background/80"
                />
              </div>
            </div>

            {/* RIGHT COLUMN: AI Intelligence & Crawler Runtime Controls */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground/90 uppercase tracking-wider pb-1 border-b border-border/40">
                <CpuIcon className="size-3.5 text-purple-400" />
                <span>AI Model &amp; Execution</span>
              </div>

              {/* AI Model Selection */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold flex items-center gap-1.5">
                  <BotIcon className="size-3.5 text-purple-400" />
                  AI Intelligence Model
                </Label>
                <Select
                  value={settings.model}
                  onValueChange={(val) => setSettings({ ...settings, model: val || "gpt-4.1-mini" })}
                >
                  <SelectTrigger className="w-full text-xs font-mono bg-background/80 border-border hover:bg-muted/40 cursor-pointer h-9">
                    <SelectValue placeholder="Select Model" />
                  </SelectTrigger>
                  <SelectContent className="z-[100]">
                    <SelectItem value="gpt-4.1-mini" className="text-xs font-mono cursor-pointer">
                      GPT-4.1-mini (Azure AI Foundry / OpenAI)
                    </SelectItem>
                    <SelectItem value="gemini-3.7-flash" className="text-xs font-mono cursor-pointer">
                      Gemini 3.7 Flash (Ultra Fast)
                    </SelectItem>
                    <SelectItem value="gpt-4o-mini" className="text-xs font-mono cursor-pointer">
                      GPT-4o-mini (Fast &amp; Recommended)
                    </SelectItem>
                    <SelectItem value="gpt-4o" className="text-xs font-mono cursor-pointer">
                      GPT-4o (High Reasoning Depth)
                    </SelectItem>
                    <SelectItem value="claude-3-7-sonnet" className="text-xs font-mono cursor-pointer">
                      Claude 3.7 Sonnet (Anthropic)
                    </SelectItem>
                    <SelectItem value="ollama-local" className="text-xs font-mono cursor-pointer">
                      Ollama / Local LLM Endpoint
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Max Crawl Pages */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5">
                    <LayersIcon className="size-3.5 text-sky-400" />
                    Max Pages to Explore
                  </Label>
                  <div className="flex items-center gap-1">
                    {[5, 15, 25, 50].map((num) => (
                      <button
                        key={num}
                        type="button"
                        onClick={() => setSettings({ ...settings, maxPages: num })}
                        className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                          settings.maxPages === num
                            ? "bg-primary text-primary-foreground border-primary font-semibold"
                            : "bg-muted/40 hover:bg-muted text-muted-foreground border-border"
                        }`}
                      >
                        {num}
                      </button>
                    ))}
                  </div>
                </div>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={settings.maxPages}
                  onChange={(e) => setSettings({ ...settings, maxPages: parseInt(e.target.value) || 10 })}
                  className="text-xs font-mono h-9 bg-background/80"
                />
              </div>

              {/* Stealth & JS Rendering Toggles Container */}
              <div className="p-3.5 rounded-xl border border-border/70 bg-muted/20 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="font-semibold text-foreground text-xs">Playwright JS Rendering</p>
                    <p className="text-[10px] text-muted-foreground">Executes Single Page Apps (React/Vue/Next)</p>
                  </div>
                  <Switch
                    className="cursor-pointer scale-90"
                    checked={settings.jsRendering}
                    onCheckedChange={(val) => setSettings({ ...settings, jsRendering: val })}
                  />
                </div>

                <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40">
                  <div>
                    <p className="font-semibold text-foreground text-xs flex items-center gap-1">
                      Anti-Bot Stealth Engine
                    </p>
                    <p className="text-[10px] text-muted-foreground">Spoofs WebGL signatures &amp; headers</p>
                  </div>
                  <Switch
                    className="cursor-pointer scale-90"
                    checked={settings.stealthMode}
                    onCheckedChange={(val) => setSettings({ ...settings, stealthMode: val })}
                  />
                </div>

                <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40">
                  <div>
                    <p className="font-semibold text-foreground text-xs">Human-in-the-Loop Gate</p>
                    <p className="text-[10px] text-muted-foreground">Pause for schema review before export</p>
                  </div>
                  <Switch
                    className="cursor-pointer scale-90"
                    checked={settings.requireReview}
                    onCheckedChange={(val) => setSettings({ ...settings, requireReview: val })}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Fixed Footer */}
        <DialogFooter className="p-4 px-5 border-t border-border/60 bg-muted/20 shrink-0 flex items-center justify-between sm:justify-between w-full">
          <Button
            variant="outline"
            size="sm"
            disabled={isSubmitting}
            onClick={() => onOpenChange(false)}
            className="cursor-pointer h-9 px-4 text-xs"
          >
            Cancel
          </Button>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-block text-[11px] text-muted-foreground font-mono">
              {settings.maxPages} Pages • {settings.model}
            </span>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!canSubmit}
              className="bg-primary text-primary-foreground font-semibold cursor-pointer shadow-sm hover:opacity-95 disabled:opacity-50 h-9 px-4 text-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2Icon className="size-3.5 mr-1.5 animate-spin" />
                  Launching Exploration...
                </>
              ) : !hasUrl ? (
                "Enter Target URL"
              ) : domainVerified === false && !settings.tosAccepted ? (
                "Accept ToS to Continue"
              ) : (
                <>
                  <PlayIcon className="size-3.5 mr-1.5 fill-current" />
                  Launch Autonomous Crawl
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
