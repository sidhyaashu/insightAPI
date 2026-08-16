"use client";

import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@/components/ui/dropdown-menu";
import { ChevronDownIcon, CheckIcon, SparklesIcon, CpuIcon, ZapIcon, LayersIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export interface ModelSelection {
  model: string;
  effort: "Fast" | "Medium" | "Deep";
}

interface ClaudeModelSelectorProps {
  value: ModelSelection;
  onChange: (val: ModelSelection) => void;
}

export function ClaudeModelSelector({ value, onChange }: ClaudeModelSelectorProps) {
  const [open, setOpen] = useState(false);

  const getModelLabel = (modelId: string) => {
    switch (modelId) {
      case "gemini-3.7-flash":
        return "Gemini 3.7 Flash";
      case "gpt-4.1-mini":
        return "GPT-4.1 Mini";
      case "gpt-4o":
        return "GPT-4o Pro";
      case "gpt-4o-mini":
        return "GPT-4o Mini";
      case "ollama-local":
        return "Ollama Local";
      default:
        return "Gemini 3.7 Flash";
    }
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors focus:outline-none cursor-pointer border border-transparent hover:border-border/40"
      >
        <SparklesIcon className="size-3.5 text-primary" />
        <span className="font-semibold text-foreground">
          {getModelLabel(value.model)}
        </span>
        <span className="text-[11px] text-muted-foreground font-mono">({value.effort})</span>
        <ChevronDownIcon className="size-3 text-muted-foreground" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-80 p-2 shadow-2xl rounded-2xl bg-card border border-border">
        {/* Model Tiers */}
        <div className="space-y-1 p-1">
          {/* Gemini 3.7 Flash (Default) */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gemini-3.7-flash" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">Gemini 3.7 Flash</span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 border-primary/40 text-primary font-mono bg-primary/10">
                  ULTRA FAST
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">High-speed API intelligence with deep reasoning</p>
            </div>
            {value.model === "gemini-3.7-flash" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>

          {/* GPT-4.1 Mini (Azure AI Foundry) */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gpt-4.1-mini" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">GPT-4.1 Mini</span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 border-blue-500/40 text-blue-400 font-mono bg-blue-500/10">
                  AZURE FOUNDRY
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">High performance Azure OpenAI reasoning deployment</p>
            </div>
            {value.model === "gpt-4.1-mini" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>

          {/* GPT-4o Pro */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gpt-4o" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">GPT-4o Pro</span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 border-purple-500/40 text-purple-400 font-mono">
                  PRO
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">Advanced reasoning for complex authentication & SPAs</p>
            </div>
            {value.model === "gpt-4o" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>

          {/* GPT-4o Mini */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gpt-4o-mini" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">GPT-4o Mini</span>
              </div>
              <p className="text-[11px] text-muted-foreground">Lightweight model for everyday queries</p>
            </div>
            {value.model === "gpt-4o-mini" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>

          {/* Ollama Local */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "ollama-local" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">Ollama Local</span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 font-mono text-muted-foreground">
                  LOCAL
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">Air-gapped on-device model execution</p>
            </div>
            {value.model === "ollama-local" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>
        </div>

        <DropdownMenuSeparator className="my-1.5" />

        {/* Reasoning Effort Submenu */}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center justify-between p-2 rounded-xl text-xs font-medium cursor-pointer">
            <span className="text-muted-foreground">Reasoning Speed</span>
            <span className="text-xs text-foreground font-semibold">{value.effort}</span>
          </DropdownMenuSubTrigger>

          <DropdownMenuSubContent className="w-48 p-1.5 shadow-2xl rounded-xl bg-card border border-border">
            <DropdownMenuRadioGroup
              value={value.effort}
              onValueChange={(val) => onChange({ ...value, effort: val as "Fast" | "Medium" | "Deep" })}
            >
              <DropdownMenuRadioItem value="Fast" className="cursor-pointer text-xs py-2 rounded-lg">
                <ZapIcon className="size-3.5 mr-2 text-emerald-500" />
                <span>Fast (Low Latency)</span>
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="Medium" className="cursor-pointer text-xs py-2 rounded-lg">
                <CpuIcon className="size-3.5 mr-2 text-primary" />
                <span>Medium (Balanced)</span>
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="Deep" className="cursor-pointer text-xs py-2 rounded-lg">
                <LayersIcon className="size-3.5 mr-2 text-purple-400" />
                <span>Deep (Extensive Code)</span>
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
