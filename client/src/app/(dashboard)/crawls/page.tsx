"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import Link from "next/link";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Trash2Icon, RefreshCwIcon, PlusIcon, GlobeIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react";

export default function CrawlsHistoryPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const { data: crawls = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["crawls", page, pageSize],
    queryFn: () => crawlsApi.listCrawls(pageSize, page * pageSize),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => crawlsApi.deleteCrawl(id),
    onSuccess: () => {
      toast.success("Crawl session deleted.");
      queryClient.invalidateQueries({ queryKey: ["crawls"] });
    },
    onError: () => {
      toast.error("Failed to delete crawl session.");
    },
  });

  const filteredCrawls = crawls.filter((c) => {
    if (statusFilter === "ALL") return true;
    return c.status.toLowerCase() === statusFilter.toLowerCase();
  });

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6 font-sans">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-border/60">
        <div>
          <h1 className="text-xl font-bold tracking-tight mb-1">Crawl History</h1>
          <p className="text-xs text-muted-foreground">Historical API discovery sessions for your account.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs">
            <RefreshCwIcon className="size-3.5 mr-1" /> Refresh
          </Button>
          <Button render={<Link href="/dashboard" />} size="sm" className="text-xs bg-primary text-primary-foreground">
            <PlusIcon className="size-3.5 mr-1" /> New Crawl
          </Button>
        </div>
      </div>

      {/* Filter and Table Container */}
      <div className="border border-border/60 p-5 rounded-xl bg-card shadow-xs space-y-4">
        {/* Table Toolbar */}
        <div className="flex items-center justify-between border-b border-border/40 pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-mono">Filter Status:</span>
            {["ALL", "COMPLETED", "RUNNING", "FAILED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`text-[11px] font-mono px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                  statusFilter === st
                    ? "bg-primary text-primary-foreground font-semibold"
                    : "bg-muted/40 text-muted-foreground hover:text-foreground"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Loading Skeletons */}
        {isLoading ? (
          <div className="space-y-3 py-2">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full rounded-lg" />
            ))}
          </div>
        ) : isError ? (
          <div className="py-8 text-center space-y-2">
            <p className="text-xs text-destructive font-semibold">Failed to load crawl history.</p>
            <Button size="sm" variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        ) : filteredCrawls.length === 0 ? (
          /* Empty State CTA */
          <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
            <GlobeIcon className="size-8 text-muted-foreground/40" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-foreground">No Crawl Sessions Found</h3>
              <p className="text-xs text-muted-foreground max-w-sm">
                Start your first autonomous API discovery session to automatically extract OpenAPI 3.1 & Postman specs.
              </p>
            </div>
            <Button render={<Link href="/dashboard" />} size="sm" className="bg-primary text-primary-foreground text-xs">
              <PlusIcon className="size-3.5 mr-1" /> Start Your First Crawl
            </Button>
          </div>
        ) : (
          /* History Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border/60 text-muted-foreground font-mono">
                  <th className="pb-2.5 font-medium">Session ID</th>
                  <th className="pb-2.5 font-medium">Target URL</th>
                  <th className="pb-2.5 font-medium">Status</th>
                  <th className="pb-2.5 font-medium">Endpoints</th>
                  <th className="pb-2.5 font-medium">Created Date</th>
                  <th className="pb-2.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {filteredCrawls.map((c) => (
                  <tr key={c.session_id} className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 font-mono text-[11px] text-foreground truncate max-w-[120px]">
                      {c.session_id}
                    </td>
                    <td className="py-3 font-mono text-foreground truncate max-w-[200px]">
                      {c.target_url}
                    </td>
                    <td className="py-3">
                      <Badge
                        variant="outline"
                        className={`text-[10px] font-mono px-2 py-0.5 ${
                          c.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                            : c.status === "running"
                            ? "bg-blue-500/10 text-blue-500 border-blue-500/30 animate-pulse"
                            : "bg-destructive/10 text-destructive border-destructive/30"
                        }`}
                      >
                        {c.status}
                      </Badge>
                    </td>
                    <td className="py-3 font-mono font-bold">{c.captured_count}</td>
                    <td className="py-3 text-muted-foreground font-mono text-[11px]">
                      {new Date(c.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/crawls/${c.session_id}`}
                          className="text-xs text-primary font-medium hover:underline"
                        >
                          Live Stream
                        </Link>
                        {c.status === "completed" && (
                          <Link
                            href={`/reports/${c.session_id}`}
                            className="text-xs text-foreground font-medium hover:underline"
                          >
                            Specs
                          </Link>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => {
                            if (confirm(`Delete crawl session ${c.session_id}?`)) {
                              deleteMutation.mutate(c.session_id);
                            }
                          }}
                        >
                          <Trash2Icon className="size-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="flex items-center justify-between pt-3 border-t border-border/40 text-xs font-mono">
          <span className="text-muted-foreground">
            Page {page + 1} ({crawls.length} items)
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="h-7 text-xs"
            >
              <ChevronLeftIcon className="size-3.5 mr-1" /> Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={crawls.length < pageSize}
              onClick={() => setPage((p) => p + 1)}
              className="h-7 text-xs"
            >
              Next <ChevronRightIcon className="size-3.5 ml-1" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
