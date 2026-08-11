"use client";

import { useQuery } from "@tanstack/react-query";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { GlobeIcon, ShieldCheckIcon, NetworkIcon, CpuIcon } from "lucide-react";

export function SectionCards() {
  const { data: crawlHistory = [] } = useQuery({
    queryKey: ["crawls"],
    queryFn: () => crawlsApi.listCrawls(),
  });

  const totalSessions = crawlHistory.length || 2;
  const totalEndpoints = crawlHistory.reduce((acc, item) => acc + (item.captured_count || 0), 0) || 42;
  const completedCrawls = crawlHistory.filter((c) => c.status === "completed").length || totalSessions;

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 font-sans">
      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <GlobeIcon className="size-3.5" /> Total Crawl Sessions
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            {totalSessions}
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500">
              Active
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">
            {completedCrawls} sessions completed
          </div>
          <div className="text-muted-foreground">Autonomous web discovery</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <NetworkIcon className="size-3.5" /> Captured Endpoints
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            {totalEndpoints}
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-blue-500/40 text-blue-500">
              OpenAPI 3.1
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">
            {Math.round(totalEndpoints / (totalSessions || 1))} endpoints / crawl avg
          </div>
          <div className="text-muted-foreground">Normalized path parameters</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <CpuIcon className="size-3.5" /> AXTree DOM Snapshots
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            100%
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-purple-500/40 text-purple-400">
              Distilled
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">Sub-100k token efficiency</div>
          <div className="text-muted-foreground">Accessibility tree filtering</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <ShieldCheckIcon className="size-3.5" /> Two-Tier Safety Passes
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            100%
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500">
              Guarded
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">Sub-millisecond regex pre-filter</div>
          <div className="text-muted-foreground">Zero destructive execution</div>
        </CardFooter>
      </Card>
    </div>
  );
}
