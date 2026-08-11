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

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger
        className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors focus:outline-none cursor-pointer border border-transparent hover:border-border/40"
      >
        <span className="font-semibold text-foreground">
          {value.model === "gpt-4o" ? "Insight-4o Pro" : value.model === "ollama-local" ? "Ollama Local" : "Insight-4o Mini"}
        </span>
        <span className="text-[11px] text-muted-foreground">{value.effort}</span>
        <ChevronDownIcon className="size-3 text-muted-foreground" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-72 p-2 shadow-2xl rounded-2xl bg-card border border-border">
        {/* Model Tiers */}
        <div className="space-y-1 p-1">
          {/* Insight-4o Pro */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gpt-4o" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">Insight-4o Pro</span>
                <Badge variant="outline" className="text-[9px] px-1 py-0 border-purple-500/40 text-purple-400 font-mono">
                  PRO
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground">For complex authentication & SPA workflows</p>
            </div>
            {value.model === "gpt-4o" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>

          {/* Insight-4o Mini (Default) */}
          <DropdownMenuItem
            onClick={() => onChange({ ...value, model: "gpt-4o-mini" })}
            className="flex items-start justify-between p-2.5 rounded-xl cursor-pointer hover:bg-muted/70 transition-colors"
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-foreground">Insight-4o Mini</span>
              </div>
              <p className="text-[11px] text-muted-foreground">Most efficient for everyday API discovery</p>
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
              </div>
              <p className="text-[11px] text-muted-foreground">Air-gapped offline model execution</p>
            </div>
            {value.model === "ollama-local" && <CheckIcon className="size-4 text-primary shrink-0 mt-0.5" />}
          </DropdownMenuItem>
        </div>

        <DropdownMenuSeparator className="my-1.5" />

        {/* Effort Submenu */}
        <DropdownMenuSub>
          <DropdownMenuSubTrigger className="flex items-center justify-between p-2 rounded-xl text-xs font-medium cursor-pointer">
            <span className="text-muted-foreground">Reasoning Effort</span>
            <span className="text-xs text-foreground font-semibold">{value.effort} &gt;</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent className="w-40 p-1 rounded-xl shadow-xl">
            <DropdownMenuItem
              onClick={() => onChange({ ...value, effort: "Fast" })}
              className="text-xs cursor-pointer flex items-center justify-between p-2"
            >
              <span>Fast (Sub-second)</span>
              {value.effort === "Fast" && <CheckIcon className="size-3.5 text-primary" />}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onChange({ ...value, effort: "Medium" })}
              className="text-xs cursor-pointer flex items-center justify-between p-2"
            >
              <span>Medium (Standard)</span>
              {value.effort === "Medium" && <CheckIcon className="size-3.5 text-primary" />}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onChange({ ...value, effort: "Deep" })}
              className="text-xs cursor-pointer flex items-center justify-between p-2"
            >
              <span>Deep (Thorough)</span>
              {value.effort === "Deep" && <CheckIcon className="size-3.5 text-primary" />}
            </DropdownMenuItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
