"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import { LockedFeature } from "@/components/ui/LockedFeature";
import { toast } from "sonner";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CopyIcon, ArrowLeftIcon, RefreshCwIcon } from "lucide-react";

export default function ReportViewPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const sessionId = resolvedParams.id;
  const [activeTab, setActiveTab] = useState<"openapi" | "postman" | "markdown">("markdown");

  const { data: report, isLoading, isError, refetch } = useQuery({
    queryKey: ["report", sessionId],
    queryFn: () => crawlsApi.getReport(sessionId),
  });

  const handleCopy = () => {
    const text =
      activeTab === "markdown"
        ? report?.markdown_docs || ""
        : JSON.stringify(activeTab === "openapi" ? report?.openapi_spec : report?.postman_collection, null, 2);
    navigator.clipboard.writeText(text);
    toast.success("Documentation spec copied to clipboard!");
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6 font-sans">
      <div className="flex justify-between items-center pb-3 border-b border-border/60">
        <div>
          <h1 className="text-xl font-bold tracking-tight mb-1">Generated API Documentation</h1>
          <p className="text-xs font-mono text-muted-foreground">Session ID: {sessionId}</p>
        </div>
        <Button variant="outline" size="sm" render={<Link href="/crawls" />} className="text-xs">
          <ArrowLeftIcon className="size-3.5 mr-1" /> Back to Crawls
        </Button>
      </div>

      {/* Tabs with Tier Lock Wrappers */}
      <div className="flex border-b border-border/60 gap-4 text-xs font-mono items-center">
        <button
          onClick={() => setActiveTab("markdown")}
          className={`pb-2 border-b-2 transition cursor-pointer ${
            activeTab === "markdown" ? "border-primary text-foreground font-bold" : "border-transparent text-muted-foreground"
          }`}
        >
          Markdown Reference (Free)
        </button>

        <LockedFeature requiredTier="STARTER" featureName="OpenAPI Export">
          <button
            onClick={() => setActiveTab("openapi")}
            className={`pb-2 border-b-2 transition cursor-pointer ${
              activeTab === "openapi" ? "border-primary text-foreground font-bold" : "border-transparent text-muted-foreground"
            }`}
          >
            OpenAPI 3.1 (JSON)
          </button>
        </LockedFeature>

        <LockedFeature requiredTier="STARTER" featureName="Postman Export">
          <button
            onClick={() => setActiveTab("postman")}
            className={`pb-2 border-b-2 transition cursor-pointer ${
              activeTab === "postman" ? "border-primary text-foreground font-bold" : "border-transparent text-muted-foreground"
            }`}
          >
            Postman v2.1 Collection
          </button>
        </LockedFeature>
      </div>

      {/* Spec Output Box */}
      <div className="border border-border/60 rounded-xl bg-card p-6 shadow-xs">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-64 w-full rounded-lg" />
          </div>
        ) : isError ? (
          <div className="py-8 text-center space-y-3">
            <p className="text-xs text-destructive font-semibold">Failed to load generated report for session {sessionId}.</p>
            <Button size="sm" variant="outline" onClick={() => refetch()}>
              <RefreshCwIcon className="size-3.5 mr-1" /> Retry Loading
            </Button>
          </div>
        ) : (
          <div>
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-semibold uppercase font-mono text-muted-foreground">{activeTab} Output</span>
              <Button onClick={handleCopy} size="sm" variant="outline" className="text-xs">
                <CopyIcon className="size-3.5 mr-1" /> Copy to Clipboard
              </Button>
            </div>

            <pre className="bg-muted/40 p-4 rounded-lg text-xs font-mono overflow-x-auto max-h-[480px] border border-border/40 text-foreground leading-relaxed">
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
