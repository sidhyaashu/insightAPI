"use client";

import { useState } from "react";
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
import { SlidersIcon, ShieldCheckIcon, BotIcon, GlobeIcon } from "lucide-react";

export interface CrawlSettings {
  targetUrl: string;
  maxPages: number;
  jsRendering: boolean;
  stealthMode: boolean;
  model: string;
  authHeader: string;
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
    model: initialSettings?.model || "gpt-4o-mini",
    authHeader: initialSettings?.authHeader || "",
  });

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
            Configure agentic crawler behavior, anti-bot stealth, and model selection.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2 text-xs">
          {/* Target Web App URL */}
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold flex items-center gap-1.5">
              <GlobeIcon className="size-3.5 text-primary" />
              Target Web Application URL
            </Label>
            <Input
              placeholder="https://api.example.com"
              value={settings.targetUrl}
              onChange={(e) => setSettings({ ...settings, targetUrl: e.target.value })}
              className="text-xs font-mono"
            />
          </div>

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
          <Button size="sm" onClick={handleSave} className="bg-primary text-primary-foreground">
            Save & Apply
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
