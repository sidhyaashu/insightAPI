"use client";

import { useQuery } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import Link from "next/link";

export default function CrawlsHistoryPage() {
  const { data: crawls, isLoading, refetch } = useQuery({
    queryKey: ["crawls", "all"],
    queryFn: () => crawlsApi.listCrawls(50),
  });

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight mb-1">Crawl History</h1>
          <p className="text-sm text-muted-foreground">All historical API discovery runs for your account</p>
        </div>
        <button
          onClick={() => refetch()}
          className="text-xs border px-3 py-1.5 rounded-lg hover:bg-muted font-medium"
        >
          Refresh List
        </button>
      </div>

      <div className="border border-border p-6 rounded-xl bg-card shadow-sm">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading history...</p>
        ) : !crawls || crawls.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">No crawl history found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-xs text-muted-foreground">
                  <th className="pb-3 font-medium">Session ID</th>
                  <th className="pb-3 font-medium">Target URL</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Endpoints</th>
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {crawls.map((c) => (
                  <tr key={c.session_id} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-3 font-mono text-xs truncate max-w-[120px]">{c.session_id}</td>
                    <td className="py-3 truncate max-w-[240px]">{c.target_url}</td>
                    <td className="py-3">
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded font-medium ${
                          c.status === "completed"
                            ? "bg-green-500/10 text-green-500"
                            : c.status === "running"
                            ? "bg-blue-500/10 text-blue-500"
                            : "bg-red-500/10 text-red-500"
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 font-mono">{c.captured_count}</td>
                    <td className="py-3 text-xs text-muted-foreground">
                      {new Date(c.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 flex gap-3">
                      <Link href={`/crawls/${c.session_id}`} className="text-xs text-primary hover:underline">
                        Live Stream
                      </Link>
                      {c.status === "completed" && (
                        <Link href={`/reports/${c.session_id}`} className="text-xs text-primary hover:underline">
                          View Specs
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
