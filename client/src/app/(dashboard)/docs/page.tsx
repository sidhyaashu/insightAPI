"use client";

import React from "react";
import { Terminal, Code2, Network, ArrowRight, ShieldCheck, Layers, BookOpen } from "lucide-react";

export default function TechnicalDocsPage() {
  return (
    <div className="flex flex-1 flex-col gap-6 max-w-5xl w-full mx-auto px-4 lg:px-6 py-4 font-sans">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border/60">
        <div>
          <h1 className="text-base font-bold tracking-tight text-foreground flex items-center gap-2 font-mono">
            <BookOpen className="size-4 text-muted-foreground" /> Technical Documentation & SDK Setup
          </h1>
          <p className="text-xs text-muted-foreground">
            Python SDK, CLI Engine commands, and REST Gateway API integration.
          </p>
        </div>
      </div>

      {/* Top Quick Cards */}
      <div className="grid auto-rows-min gap-4 md:grid-cols-3">
        <div className="p-5 rounded-xl border border-border/60 bg-card flex flex-col justify-between space-y-3 shadow-xs">
          <div className="flex items-center gap-2 text-foreground font-bold text-xs font-mono">
            <Terminal className="size-4 text-muted-foreground" /> Python SDK
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Zero-dependency in-memory session mode for local Python scripts and pytest CI workflows.
          </p>
          <a href="#python-sdk" className="text-xs text-foreground font-semibold flex items-center gap-1 hover:underline pt-1">
            View Setup Guide <ArrowRight className="size-3" />
          </a>
        </div>

        <div className="p-5 rounded-xl border border-border/60 bg-card flex flex-col justify-between space-y-3 shadow-xs">
          <div className="flex items-center gap-2 text-foreground font-bold text-xs font-mono">
            <Code2 className="size-4 text-muted-foreground" /> CLI Engine
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Typer-based terminal CLI with Rich progress outputs for local runs & GitHub Actions pipelines.
          </p>
          <a href="#cli-engine" className="text-xs text-foreground font-semibold flex items-center gap-1 hover:underline pt-1">
            View CLI Commands <ArrowRight className="size-3" />
          </a>
        </div>

        <div className="p-5 rounded-xl border border-border/60 bg-card flex flex-col justify-between space-y-3 shadow-xs">
          <div className="flex items-center gap-2 text-foreground font-bold text-xs font-mono">
            <Network className="size-4 text-muted-foreground" /> REST Gateway API
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            FastAPI backend API endpoints with JWT auth, WebSocket streams, and Postgres storage.
          </p>
          <a href="#gateway-endpoints" className="text-xs text-foreground font-semibold flex items-center gap-1 hover:underline pt-1">
            View API Endpoints <ArrowRight className="size-3" />
          </a>
        </div>
      </div>

      {/* 1. Python SDK Section */}
      <section id="python-sdk" className="border border-border/60 p-6 rounded-xl bg-card space-y-3 shadow-xs">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm font-mono">
          <Terminal className="size-4 text-muted-foreground" /> Python SDK Setup & Reference
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Install the open-source SDK from PyPI and run zero-dependency in-memory crawls inside your test suites or automation scripts:
        </p>

        <pre className="bg-muted/50 p-3 rounded-lg text-xs font-mono border border-border/60 text-foreground">
          pip install insightapi
        </pre>

        <pre className="bg-muted/70 text-foreground p-4 rounded-lg text-xs font-mono overflow-x-auto border border-border/60 leading-relaxed">
{`import asyncio
from insightapi import AgentEngine

async def main():
    engine = AgentEngine()
    results = await engine.crawl("https://example.com/app", max_pages=15)
    
    print(f"Captured {len(results.captured_endpoints)} endpoints")
    
    # Export specs
    openapi_json = results.to_openapi()
    postman_json = results.to_postman()

asyncio.run(main())`}
        </pre>
      </section>

      {/* 2. CLI Tool Section */}
      <section id="cli-engine" className="border border-border/60 p-6 rounded-xl bg-card space-y-3 shadow-xs">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm font-mono">
          <Code2 className="size-4 text-muted-foreground" /> CLI Engine Commands
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Use the Typer-based CLI for local development or embed it directly into GitHub Actions / GitLab CI pipelines:
        </p>

        <pre className="bg-muted/50 p-3 rounded-lg text-xs font-mono border border-border/60 text-foreground">
          insightapi crawl https://example.com --max-pages 20 --output ./openapi.json
        </pre>
      </section>

      {/* 3. Safety Guardrails & Architecture Section */}
      <section id="gateway-endpoints" className="border border-border/60 p-6 rounded-xl bg-card space-y-3 shadow-xs">
        <div className="flex items-center gap-2 text-foreground font-bold text-sm font-mono">
          <ShieldCheck className="size-4 text-muted-foreground" /> Two-Tier Safety Guardrails & AXTree
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          InsightAPI uses a sub-millisecond Two-Tier Risk Classifier to prevent destructive actions (e.g. DELETE requests or payment submissions) during automated exploration:
        </p>

        <div className="grid sm:grid-cols-2 gap-3 pt-1">
          <div className="p-4 rounded-lg bg-muted/40 border border-border/40 space-y-1">
            <h4 className="font-mono font-bold text-xs text-foreground flex items-center gap-1.5">
              <Layers className="size-3.5" /> Tier 1: Regex Guardrails
            </h4>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Sub-millisecond regex pre-filtering for obvious SAFE navigation targets vs UNSAFE actions.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-muted/40 border border-border/40 space-y-1">
            <h4 className="font-mono font-bold text-xs text-foreground flex items-center gap-1.5">
              <ShieldCheck className="size-3.5 text-emerald-500" /> Tier 2: Context Enrichment
            </h4>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Evaluates surrounding form labels and parent headers for ambiguous submit buttons.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
