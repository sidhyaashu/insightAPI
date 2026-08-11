"use client";

import React from "react";
import { AppSidebar } from "@/components/app-sidebar";
import { SiteHeader } from "@/components/site-header";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { Terminal, Code2, Network, ArrowRight } from "lucide-react";

export default function TechnicalDocsPage() {
  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset className="bg-background text-foreground">
        <SiteHeader />

        <div className="flex flex-1 flex-col gap-6 p-6 md:p-8 max-w-6xl w-full mx-auto">
          {/* Top Quick Cards */}
          <div className="grid auto-rows-min gap-4 md:grid-cols-3">
            <div className="p-6 rounded-xl border border-border bg-card/40 flex flex-col justify-between space-y-3">
              <div className="flex items-center gap-2 text-primary font-bold text-sm">
                <Terminal className="h-4 w-4" /> Python SDK
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Zero-dependency in-memory session mode for local python scripts and pytest CI workflows.
              </p>
              <a href="#python-sdk" className="text-xs text-primary font-semibold flex items-center gap-1 hover:underline pt-2">
                View Setup Guide <ArrowRight className="h-3 w-3" />
              </a>
            </div>

            <div className="p-6 rounded-xl border border-border bg-card/40 flex flex-col justify-between space-y-3">
              <div className="flex items-center gap-2 text-blue-500 font-bold text-sm">
                <Code2 className="h-4 w-4" /> CLI Engine
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Typer-based terminal CLI with Rich progress outputs for local runs & GitHub Actions pipelines.
              </p>
              <a href="#cli-engine" className="text-xs text-blue-500 font-semibold flex items-center gap-1 hover:underline pt-2">
                View CLI Commands <ArrowRight className="h-3 w-3" />
              </a>
            </div>

            <div className="p-6 rounded-xl border border-border bg-card/40 flex flex-col justify-between space-y-3">
              <div className="flex items-center gap-2 text-green-500 font-bold text-sm">
                <Network className="h-4 w-4" /> REST Gateway API
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                FastAPI backend API endpoints with JWT auth, WebSocket streams, and Postgres pgvector storage.
              </p>
              <a href="#gateway-endpoints" className="text-xs text-green-500 font-semibold flex items-center gap-1 hover:underline pt-2">
                View API Endpoints <ArrowRight className="h-3 w-3" />
              </a>
            </div>
          </div>

          {/* 1. Python SDK Section */}
          <section id="python-sdk" className="border border-border p-6 sm:p-8 rounded-xl bg-card">
            <div className="flex items-center gap-2 mb-2 text-primary font-bold text-lg">
              <Terminal className="h-5 w-5" /> Python SDK Setup & Reference
            </div>
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
              Install the open-source SDK from PyPI and run zero-dependency in-memory crawls inside your test suites or automation scripts:
            </p>

            <pre className="bg-muted p-4 rounded-lg text-xs font-mono mb-4 border">
              pip install insightapi
            </pre>

            <pre className="bg-black text-green-400 p-4 rounded-lg text-xs font-mono overflow-x-auto">
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
          <section id="cli-engine" className="border border-border p-6 sm:p-8 rounded-xl bg-card">
            <div className="flex items-center gap-2 mb-2 text-blue-500 font-bold text-lg">
              <Code2 className="h-5 w-5" /> CLI Engine Usage
            </div>
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
              Use the Typer-based CLI for local development or embed it directly into GitHub Actions / GitLab CI pipelines:
            </p>

            <pre className="bg-black text-green-400 p-4 rounded-lg text-xs font-mono overflow-x-auto">
{`# Run interactive crawl with live Rich progress output
insightapi crawl https://example.com/app --max-pages 20 --output-dir ./specs

# Generate exports from previous run
insightapi export openapi --input ./specs/session.json --output openapi.json`}
            </pre>
          </section>

          {/* 3. Gateway REST & WebSocket Endpoints */}
          <section id="gateway-endpoints" className="border border-border p-6 sm:p-8 rounded-xl bg-card">
            <div className="flex items-center gap-2 mb-2 text-green-500 font-bold text-lg">
              <Network className="h-5 w-5" /> API Gateway Endpoints
            </div>
            <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
              All requests pass through the API Gateway with JWT validation and header injection:
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="pb-2">Method</th>
                    <th className="pb-2">Endpoint</th>
                    <th className="pb-2">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  <tr>
                    <td className="py-2 text-blue-500 font-bold">GET</td>
                    <td className="py-2">/api/auth/github/login</td>
                    <td className="py-2 text-foreground font-sans">Redirect to GitHub OAuth screen</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-blue-500 font-bold">GET</td>
                    <td className="py-2">/api/auth/google/login</td>
                    <td className="py-2 text-foreground font-sans">Redirect to Google OAuth screen</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-green-500 font-bold">POST</td>
                    <td className="py-2">/api/auth/login</td>
                    <td className="py-2 text-foreground font-sans">Email/Password authentication</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-green-500 font-bold">POST</td>
                    <td className="py-2">/api/auth/refresh</td>
                    <td className="py-2 text-foreground font-sans">Rotate refresh token (HttpOnly cookie)</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-green-500 font-bold">POST</td>
                    <td className="py-2">/api/v1/crawls/start</td>
                    <td className="py-2 text-foreground font-sans">Start autonomous crawl run</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-purple-500 font-bold">WS</td>
                    <td className="py-2">/ws/crawls/{`{id}`}/stream</td>
                    <td className="py-2 text-foreground font-sans">Real-time log event stream</td>
                  </tr>
                  <tr>
                    <td className="py-2 text-purple-500 font-bold">WS</td>
                    <td className="py-2">/ws/chat/{`{session}`}</td>
                    <td className="py-2 text-foreground font-sans">AI Chatbot streaming connection</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
