"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useAppSelector, useAppDispatch } from "@/store";
import { clearCredentials } from "@/features/auth/store/authSlice";
import { authApi } from "@/features/auth/api/auth.api";
import { useRouter } from "next/navigation";
import {
  IconSearch,
  IconFilter,
  IconX,
  IconLogout,
} from "@tabler/icons-react";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

// ─── Settings Types ────────────────────────────────────────────────────────────

type SettingsTab = "user" | "workspace" | "agent";

interface SettingItem {
  id: string;
  tab: SettingsTab;
  category: string;
  labelPrefix: string;
  name: string;
  description: React.ReactNode;
  type: "select" | "text" | "number" | "toggle" | "action";
  options?: { label: string; value: string }[];
  defaultValue?: string | number | boolean;
  actionButton?: { label: string; href?: string; onClick?: () => void };
}

export default function SettingsPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);
  const { theme, setTheme } = useTheme();

  // Search & Navigation state
  const [activeTab, setActiveTab] = useState<SettingsTab>("user");
  const [activeCategory, setActiveCategory] = useState<string>("Commonly Used");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Local settings state
  const [settingsValues, setSettingsValues] = useState<Record<string, any>>({
    "editor.fontSize": 14,
    "editor.fontFamily": "JetBrains Mono, Consolas, monospace",
    "editor.tabSize": 2,
    "ai.defaultModel": "gemini-3.7-flash",
    "ai.reasoningEffort": "medium",
    "ai.autoOpenArtifacts": true,
    "crawler.maxPages": 10,
    "crawler.requestDelay": 500,
    "crawler.respectRobots": true,
    "crawler.distillationMode": "axtree",
    "crawler.autoDismissCookies": true,
    "security.twoTierGuardrails": true,
    "security.sandboxTimeout": 10,
    "security.destructiveApproval": true,
    "theme.colorMode": theme || "dark",
  });

  const handleSettingChange = (id: string, value: any) => {
    setSettingsValues((prev) => ({ ...prev, [id]: value }));
    if (id === "theme.colorMode") {
      setTheme(value);
    }
    toast.success("Setting updated", { duration: 1500 });
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    dispatch(clearCredentials());
    router.replace("/login");
  };

  // ─── Settings Master Definitions ─────────────────────────────────────────────

  const settingsList: SettingItem[] = useMemo(
    () => [
      // ── Commonly Used ──
      {
        id: "ai.defaultModel",
        tab: "user",
        category: "Commonly Used",
        labelPrefix: "AI",
        name: "Default Reasoning Model",
        description: "Controls the default LLM used for autonomous crawling, API reasoning, and chat stream.",
        type: "select",
        options: [
          { label: "Gemini 3.7 Flash (Fast Hybrid Reasoning)", value: "gemini-3.7-flash" },
          { label: "GPT-4.1 Mini (Azure AI Foundry / OpenAI)", value: "gpt-4.1-mini" },
          { label: "Claude 3.7 Sonnet (Deep Architectural Reasoning)", value: "claude-3.7-sonnet" },
          { label: "GPT-4o (Multimodal Vision & Analysis)", value: "gpt-4o" },
          { label: "GPT-4o Mini (Cost Efficient Fast)", value: "gpt-4o-mini" },
        ],
      },
      {
        id: "ai.reasoningEffort",
        tab: "user",
        category: "Commonly Used",
        labelPrefix: "AI",
        name: "Reasoning Effort",
        description: "Controls how thoroughly the LLM builds step-by-step thinking graphs prior to generating responses.",
        type: "select",
        options: [
          { label: "Low (Quick response, minimal thinking tags)", value: "low" },
          { label: "Medium (Balanced reasoning, standard architecture flows)", value: "medium" },
          { label: "High (Deep chain-of-thought, extensive edge case validation)", value: "high" },
        ],
      },
      {
        id: "crawler.maxPages",
        tab: "workspace",
        category: "Commonly Used",
        labelPrefix: "Crawler",
        name: "Max Exploration Depth",
        description: "Maximum number of distinct route pages the autonomous crawler will navigate per session.",
        type: "number",
      },
      {
        id: "security.twoTierGuardrails",
        tab: "agent",
        category: "Commonly Used",
        labelPrefix: "Security",
        name: "Two-Tier Action Guardrails",
        description: "Automatically intercepts and flags destructive API actions (delete, payment, billing, password changes) during AI security analysis.",
        type: "toggle",
      },

      // ── Profile & Account ──
      {
        id: "profile.name",
        tab: "user",
        category: "Profile & Account",
        labelPrefix: "User",
        name: "Full Name",
        description: "Your registered developer name in the platform.",
        type: "text",
        defaultValue: user?.name || "Asutosh Sidhya",
      },
      {
        id: "profile.email",
        tab: "user",
        category: "Profile & Account",
        labelPrefix: "User",
        name: "Email Address",
        description: "Primary email address associated with your InsightAPI workspace account.",
        type: "text",
        defaultValue: user?.email || "sidhyaasutosh@gmail.com",
      },
      {
        id: "profile.tier",
        tab: "user",
        category: "Profile & Account",
        labelPrefix: "User",
        name: "Account Tier & Access Level",
        description: (
          <span>
            Current tier: <strong className="text-foreground">{user?.tier || "FREE"}</strong>. Controls daily rate limits and max concurrent crawl tasks.
          </span>
        ),
        type: "action",
        actionButton: { label: "Manage Plan in Billing", href: "/billing" },
      },

      // ── AI & Reasoning ──
      {
        id: "ai.autoOpenArtifacts",
        tab: "user",
        category: "AI & Reasoning",
        labelPrefix: "AI",
        name: "Auto-Open Artifacts Workspace",
        description: "Automatically slides open the right-hand preview panel when an OpenAPI spec or Mermaid diagram is generated.",
        type: "toggle",
      },
      {
        id: "ai.systemPersona",
        tab: "agent",
        category: "AI & Reasoning",
        labelPrefix: "AI",
        name: "System Prompt Persona",
        description: "Adjusts the conversational style and technical depth of InsightBot.",
        type: "select",
        options: [
          { label: "API Architect (Developer-first, OpenAPI 3.1 & Mermaid diagrams)", value: "architect" },
          { label: "Security Auditor (OWASP Top 10 focus, vulnerability test payloads)", value: "security" },
          { label: "Concise Engineer (Minimal prose, direct code snippets)", value: "concise" },
        ],
      },

      // ── Crawler & Sandbox Engine ──
      {
        id: "crawler.distillationMode",
        tab: "workspace",
        category: "Crawler & Sandbox",
        labelPrefix: "Crawler",
        name: "DOM Distillation Architecture",
        description: "Accessibility Tree (AXTree) reduces token usage by 95% by extracting only interactive semantic controls.",
        type: "select",
        options: [
          { label: "AXTree Accessibility Distillation (Recommended, ~500 tokens)", value: "axtree" },
          { label: "Vision Set-of-Marks Fallback (Vision LLM screenshot markup)", value: "vision" },
        ],
      },
      {
        id: "crawler.requestDelay",
        tab: "workspace",
        category: "Crawler & Sandbox",
        labelPrefix: "Crawler",
        name: "Per-Domain Request Delay (ms)",
        description: "Spacing interval between consecutive automated page clicks to respect target server rate limits.",
        type: "number",
      },
      {
        id: "crawler.respectRobots",
        tab: "workspace",
        category: "Crawler & Sandbox",
        labelPrefix: "Crawler",
        name: "Enforce robots.txt Compliance",
        description: "Parses target domain robots.txt rules and skips disallowed crawl paths.",
        type: "toggle",
      },
      {
        id: "crawler.autoDismissCookies",
        tab: "workspace",
        category: "Crawler & Sandbox",
        labelPrefix: "Crawler",
        name: "Auto-Dismiss Cookie & Interstitial Modals",
        description: "Automatically detects and clicks 'Accept' / 'Close' on blocking cookie consent banners.",
        type: "toggle",
      },

      // ── Security & Guardrails ──
      {
        id: "security.sandboxTimeout",
        tab: "agent",
        category: "Security & Guardrails",
        labelPrefix: "Security",
        name: "Sandbox Egress Timeout (Seconds)",
        description: "Hard timeout cap for active vulnerability test requests executed through isolated SandboxExecutor.",
        type: "number",
      },
      {
        id: "security.destructiveApproval",
        tab: "agent",
        category: "Security & Guardrails",
        labelPrefix: "Security",
        name: "Require Human Authorization for Destructive Tests",
        description: "Requires explicit user confirmation via Security Center before executing state-modifying security test probes.",
        type: "toggle",
      },

      // ── Appearance & Editor ──
      {
        id: "theme.colorMode",
        tab: "user",
        category: "Appearance & Editor",
        labelPrefix: "Appearance",
        name: "Color Theme",
        description: "Controls the active interface color scheme across all workspace views.",
        type: "select",
        options: [
          { label: "Dark (Default, sleek high-contrast IDE)", value: "dark" },
          { label: "Light (Clean daylight theme)", value: "light" },
          { label: "System (Follows OS preference)", value: "system" },
        ],
      },
      {
        id: "editor.fontFamily",
        tab: "user",
        category: "Appearance & Editor",
        labelPrefix: "Editor",
        name: "Font Family",
        description: "Controls the font family used in the code viewer, artifact canvas, and Markdown blocks.",
        type: "text",
      },
      {
        id: "editor.fontSize",
        tab: "user",
        category: "Appearance & Editor",
        labelPrefix: "Editor",
        name: "Font Size (px)",
        description: "Controls the base font size for code editor and Markdown response panels.",
        type: "number",
      },
    ],
    [user, theme]
  );

  // Group categories
  const categories = useMemo(() => {
    const set = new Set<string>();
    settingsList.forEach((s) => set.add(s.category));
    return Array.from(set);
  }, [settingsList]);

  // Filtered settings
  const filteredSettings = useMemo(() => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      return settingsList.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.labelPrefix.toLowerCase().includes(q) ||
          s.category.toLowerCase().includes(q)
      );
    }

    if (activeCategory === "Commonly Used") {
      return settingsList.filter((s) => s.category === "Commonly Used");
    }

    return settingsList.filter((s) => s.category === activeCategory);
  }, [searchQuery, activeCategory, settingsList]);

  return (
    <div className="flex flex-col flex-1 h-full w-full bg-background text-foreground font-sans overflow-hidden select-none">
      {/* ── Top Bar: Search Settings Input (VS Code Style with shadcn Input) ── */}
      <div className="px-6 pt-4 pb-2 border-b border-border/40 shrink-0 space-y-3 bg-background">
        {/* Search Input Box */}
        <div className="relative max-w-2xl w-full">
          <IconSearch className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search settings"
            className="pl-9 pr-16 h-8 text-xs rounded-md bg-muted/30 border-border/60 placeholder:text-muted-foreground/60 focus-visible:border-blue-500 focus-visible:ring-1 focus-visible:ring-blue-500"
          />

          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1 text-muted-foreground/70">
            {searchQuery ? (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSearchQuery("")}
                className="size-5 rounded hover:text-foreground cursor-pointer"
                title="Clear search"
              >
                <IconX className="size-3" />
              </Button>
            ) : (
              <IconFilter className="size-3.5" />
            )}
          </div>
        </div>

        {/* Tab Navigation: [User] [Workspace] [Platform Engine] */}
        <div className="flex items-center gap-6 text-xs border-b border-transparent -mb-px">
          <button
            type="button"
            onClick={() => {
              setActiveTab("user");
              setSearchQuery("");
            }}
            className={`pb-2 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === "user"
                ? "border-foreground text-foreground font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            User
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab("workspace");
              setSearchQuery("");
            }}
            className={`pb-2 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === "workspace"
                ? "border-foreground text-foreground font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Workspace
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab("agent");
              setSearchQuery("");
            }}
            className={`pb-2 border-b-2 font-medium transition-colors cursor-pointer ${
              activeTab === "agent"
                ? "border-foreground text-foreground font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Platform Engine
          </button>
        </div>
      </div>

      {/* ── Main Two-Column Layout: [Sidebar Categories] [Settings List] ──── */}
      <div className="flex flex-1 min-h-0 w-full overflow-hidden">
        {/* ── Left Categories Sidebar ───────────────────────────────────── */}
        <div className="w-64 border-r border-border/40 bg-background/50 p-3 overflow-y-auto shrink-0 select-none space-y-1">
          {categories.map((cat) => {
            const isSelected = activeCategory === cat && !searchQuery;

            return (
              <button
                key={cat}
                type="button"
                onClick={() => {
                  setActiveCategory(cat);
                  setSearchQuery("");
                }}
                className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-colors cursor-pointer text-left ${
                  isSelected
                    ? "text-foreground font-bold bg-muted/60"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                }`}
              >
                <span className="truncate">{cat}</span>
              </button>
            );
          })}

          <Separator className="my-3 opacity-40" />

          {/* Quick Account Logout */}
          <div className="px-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start gap-2 text-xs text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 h-8 font-normal cursor-pointer"
            >
              <IconLogout className="size-3.5" />
              <span>Log out session</span>
            </Button>
          </div>
        </div>

        {/* ── Right Settings Content Area ──────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-8 max-w-4xl pb-28">
          {/* Active Category Heading */}
          <div className="space-y-1 border-b border-border/30 pb-3">
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              {searchQuery ? `Search results for "${searchQuery}"` : activeCategory}
            </h1>
            <p className="text-xs text-muted-foreground">
              {searchQuery
                ? `Found ${filteredSettings.length} settings matching your query.`
                : `Configure ${activeCategory.toLowerCase()} settings for your InsightAPI session.`}
            </p>
          </div>

          {/* Settings List */}
          {filteredSettings.length === 0 ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              No matching settings found.
            </div>
          ) : (
            <div className="space-y-6">
              {filteredSettings.map((item) => {
                const currentValue =
                  settingsValues[item.id] !== undefined
                    ? settingsValues[item.id]
                    : item.defaultValue;

                return (
                  <div key={item.id} className="space-y-2 group">
                    {/* Setting Title with Bold Prefix (e.g. Files: Auto Save) */}
                    <div className="flex items-center gap-1.5 text-xs text-foreground font-sans">
                      <span className="font-semibold">{item.labelPrefix}:</span>
                      <span className="font-bold text-foreground">{item.name}</span>
                    </div>

                    {/* Setting Description */}
                    <div className="text-xs text-muted-foreground leading-relaxed max-w-2xl">
                      {item.description}
                    </div>

                    {/* Setting Control Form Item with shadcn Elements */}
                    <div className="pt-1 max-w-md">
                      {item.type === "select" && item.options && (
                        <Select
                          value={currentValue}
                          onValueChange={(val) => handleSettingChange(item.id, val)}
                        >
                          <SelectTrigger className="w-full text-xs h-8 bg-muted/20 border-input">
                            <SelectValue placeholder="Select option" />
                          </SelectTrigger>
                          <SelectContent>
                            {item.options.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value} className="text-xs">
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}

                      {item.type === "text" && (
                        <Input
                          type="text"
                          value={currentValue || ""}
                          onChange={(e) => handleSettingChange(item.id, e.target.value)}
                          className="h-8 text-xs font-mono max-w-md"
                        />
                      )}

                      {item.type === "number" && (
                        <Input
                          type="number"
                          value={currentValue || 0}
                          onChange={(e) => handleSettingChange(item.id, Number(e.target.value))}
                          className="h-8 text-xs font-mono w-32"
                        />
                      )}

                      {item.type === "toggle" && (
                        <div className="flex items-center gap-3 pt-1">
                          <Switch
                            checked={!!currentValue}
                            onCheckedChange={(checked) => handleSettingChange(item.id, checked)}
                          />
                          <span className="text-xs text-muted-foreground font-medium">
                            {currentValue ? "Enabled" : "Disabled"}
                          </span>
                        </div>
                      )}

                      {item.type === "action" && item.actionButton && (
                        <Link href={item.actionButton.href || "#"}>
                          <Button
                            size="sm"
                            className="text-xs bg-primary text-primary-foreground hover:bg-primary/90 h-8 font-medium cursor-pointer"
                          >
                            {item.actionButton.label}
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
