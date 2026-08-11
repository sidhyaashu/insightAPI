"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import { LockedFeature } from "@/components/ui/LockedFeature";
import Link from "next/link";

export default function ReportViewPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const [activeTab, setActiveTab] = useState<"openapi" | "postman" | "markdown">("markdown");

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report", sessionId],
    queryFn: () => crawlsApi.getReport(sessionId),
  });

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1">Generated API Documentation</h1>
          <p className="text-xs font-mono text-muted-foreground">Session ID: {sessionId}</p>
        </div>
        <Link href="/crawls" className="text-xs border px-3 py-1.5 rounded-lg hover:bg-muted font-medium">
          &larr; Back to History
        </Link>
      </div>

      {/* Tabs with Tier Lock Wrappers */}
      <div className="flex border-b border-border gap-4 text-sm font-medium items-center">
        <button
          onClick={() => setActiveTab("markdown")}
          className={`pb-2 border-b-2 transition ${
            activeTab === "markdown" ? "border-primary text-foreground" : "border-transparent text-muted-foreground"
          }`}
        >
          Markdown Reference (Free)
        </button>

        <LockedFeature requiredTier="STARTER" featureName="OpenAPI Export">
          <button
            onClick={() => setActiveTab("openapi")}
            className={`pb-2 border-b-2 transition ${
              activeTab === "openapi" ? "border-primary text-foreground" : "border-transparent text-muted-foreground"
            }`}
          >
            OpenAPI v3.0 (JSON)
          </button>
        </LockedFeature>

        <LockedFeature requiredTier="STARTER" featureName="Postman Export">
          <button
            onClick={() => setActiveTab("postman")}
            className={`pb-2 border-b-2 transition ${
              activeTab === "postman" ? "border-primary text-foreground" : "border-transparent text-muted-foreground"
            }`}
          >
            Postman v2.1 Collection
          </button>
        </LockedFeature>
      </div>

      {/* Spec Output Box */}
      <div className="border border-border rounded-xl bg-card p-6 shadow-sm">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading report data...</p>
        ) : error ? (
          <p className="text-sm text-destructive">Failed to load report for session {sessionId}.</p>
        ) : (
          <div>
            <div className="flex justify-between items-center mb-4">
              <span className="text-xs font-semibold uppercase text-muted-foreground">{activeTab} Output</span>
              <button
                onClick={() => {
                  const text =
                    activeTab === "markdown"
                      ? report?.markdown_docs || ""
                      : JSON.stringify(activeTab === "openapi" ? report?.openapi_spec : report?.postman_collection, null, 2);
                  navigator.clipboard.writeText(text);
                  alert("Copied to clipboard!");
                }}
                className="text-xs bg-muted hover:bg-accent px-3 py-1 rounded border font-medium"
              >
                Copy to Clipboard
              </button>
            </div>

            <pre className="bg-muted p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[500px]">
              {activeTab === "markdown"
                ? report?.markdown_docs || "No markdown generated."
                : JSON.stringify(
                    activeTab === "openapi" ? report?.openapi_spec : report?.postman_collection,
                    null,
                    2
                  ) || "No specification data generated."}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
