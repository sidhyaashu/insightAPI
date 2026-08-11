"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import { useTier } from "@/hooks/useTier";
import { SectionCards } from "@/components/section-cards";
import { ChartAreaInteractive } from "@/components/chart-area-interactive";
import { DataTable } from "@/components/data-table";
import data from "../data.json";
import Link from "next/link";

export default function DashboardOverviewPage() {
  const router = useRouter();
  const { tier, isFree, isAdmin } = useTier();
  const [targetUrl, setTargetUrl] = useState("");
  const [maxPages, setMaxPages] = useState(10);
  const [goal, setGoal] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const { data: recentCrawls, isLoading } = useQuery({
    queryKey: ["crawls", "recent"],
    queryFn: () => crawlsApi.listCrawls(5),
  });

  const handleStartCrawl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl) return;
    setIsSubmitting(true);
    setErrorMsg("");

    try {
      const session = await crawlsApi.startCrawl({
        target_url: targetUrl,
        max_pages: maxPages,
        goal: goal || undefined,
      });
      router.push(`/crawls/${session.session_id}`);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || "Failed to start crawl");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Metrics Cards */}
      <SectionCards />

      {/* Crawl Launcher Box */}
      <div className="border border-border p-6 rounded-xl bg-card shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-lg font-semibold">Launch Autonomous API Crawl</h2>
            <p className="text-xs text-muted-foreground">
              Current Tier: <span className="font-semibold text-foreground">{tier}</span>
              {isFree ? " (1 crawl / day limit)" : isAdmin ? " (👑 Unlimited Admin Privileges)" : " (Unlocked)"}
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded-lg">
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleStartCrawl} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium mb-1">Target Application URL</label>
            <input
              type="url"
              required
              placeholder="https://example.com/app"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium mb-1">Max Exploration Pages</label>
              <input
                type="number"
                min={1}
                max={isAdmin ? 1000 : isFree ? 10 : 200}
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                className="w-full px-4 py-2 border rounded-lg bg-background text-sm"
              />
              <span className="text-[11px] text-muted-foreground mt-0.5 block">
                {isAdmin ? "Admin limit: 1000 pages" : isFree ? "Free tier max: 10 pages" : "Max 200 pages"}
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">Goal / Exploration Focus (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Find user settings and payment endpoints"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg bg-background text-sm"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 bg-primary text-primary-foreground py-2.5 px-6 rounded-lg font-medium text-sm self-start hover:opacity-90 disabled:opacity-50"
          >
            {isSubmitting ? "Starting Crawl Engine..." : "Start Autonomous Crawl"}
          </button>
        </form>
      </div>

      {/* Interactive Visitors Chart */}
      <div>
        <ChartAreaInteractive />
      </div>

      {/* Data Table */}
      <div>
        <DataTable data={data} />
      </div>
    </div>
  );
}
