"use client";

import React from "react";
import Link from "next/link";
import {
  IconMessage,
  IconSparkles,
  IconCode,
  IconShieldLock,
  IconBrain,
  IconArrowRight,
} from "@tabler/icons-react";
import { Button } from "@/components/ui/button";

export default function ReportsOverviewPage() {
  return (
    <div className="flex flex-col flex-1 gap-6 p-6 max-w-5xl mx-auto w-full font-sans">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <IconSparkles className="size-6 text-primary" />
            API Intelligence &amp; Artifacts
          </h1>
          <p className="text-xs text-muted-foreground">
            All API specifications, OpenAPI 3.1 schemas, Postman collections, and security analyses are generated interactively inside the AI Chat workspace.
          </p>
        </div>
        <Link href="/chat">
          <Button className="bg-primary text-primary-foreground text-xs flex items-center gap-2 shadow-xs cursor-pointer">
            <IconMessage className="size-4" />
            Open AI Chat
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
        <div className="p-5 rounded-2xl border border-border/60 bg-card space-y-3">
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary w-fit">
            <IconCode className="size-5" />
          </div>
          <h2 className="text-sm font-semibold text-foreground">Interactive OpenAPI 3.1 Specs</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Generate and inspect schemas in real time. Full specifications appear in the side-by-side Artifact Panel with one-click export.
          </p>
          <Link href="/chat" className="text-xs text-primary font-medium flex items-center gap-1 hover:underline pt-1">
            Generate in Chat <IconArrowRight className="size-3" />
          </Link>
        </div>

        <div className="p-5 rounded-2xl border border-border/60 bg-card space-y-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-500 w-fit">
            <IconShieldLock className="size-5" />
          </div>
          <h2 className="text-sm font-semibold text-foreground">Security &amp; Auth Verification</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Validate Bearer tokens, API keys, and CORS permissions with step-by-step reasoning and safety guardrails.
          </p>
          <Link href="/chat" className="text-xs text-emerald-500 font-medium flex items-center gap-1 hover:underline pt-1">
            Analyze in Chat <IconArrowRight className="size-3" />
          </Link>
        </div>

        <div className="p-5 rounded-2xl border border-border/60 bg-card space-y-3">
          <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500 w-fit">
            <IconBrain className="size-5" />
          </div>
          <h2 className="text-sm font-semibold text-foreground">cURL &amp; Architecture Diagrams</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Paste raw cURL requests to automatically generate Mermaid architecture diagrams and executable Postman collections.
          </p>
          <Link href="/chat" className="text-xs text-blue-500 font-medium flex items-center gap-1 hover:underline pt-1">
            Debug in Chat <IconArrowRight className="size-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
