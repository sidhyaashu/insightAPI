"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { MessageSquareIcon, ShieldCheckIcon, NetworkIcon, CpuIcon } from "lucide-react";
import { useAppSelector } from "@/store";

export function SectionCards() {
  const { sessions } = useAppSelector((state) => state.chat);
  const totalSessions = sessions.length || 1;

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4 font-sans">
      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <MessageSquareIcon className="size-3.5 text-primary" /> Active AI Chat Sessions
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            {totalSessions}
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500">
              Live
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">
            DB-Persisted History
          </div>
          <div className="text-muted-foreground">Conversational API Intelligence</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <NetworkIcon className="size-3.5 text-blue-500" /> OpenAPI 3.1 &amp; Postman
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            Artifacts
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-blue-500/40 text-blue-500">
              Interactive
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">
            Real-time projection
          </div>
          <div className="text-muted-foreground">Side-by-side artifact viewer</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <CpuIcon className="size-3.5 text-purple-400" /> Real-time Reasoning
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            &lt;think&gt;
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-purple-500/40 text-purple-400">
              Streaming
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">Chain of Thought Enabled</div>
          <div className="text-muted-foreground">Transparent multi-step reasoning</div>
        </CardFooter>
      </Card>

      <Card className="@container/card bg-card border-border/60">
        <CardHeader>
          <CardDescription className="font-mono text-xs text-muted-foreground flex items-center gap-1.5">
            <ShieldCheckIcon className="size-3.5 text-emerald-500" /> Multi-Model Routing
          </CardDescription>
          <CardTitle className="text-2xl font-bold font-mono text-foreground">
            Multi-LLM
          </CardTitle>
          <CardAction>
            <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/40 text-emerald-500">
              Active
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1 text-xs">
          <div className="font-medium text-foreground">Claude / Gemini / Azure OpenAI</div>
          <div className="text-muted-foreground">Model routing with daily quotas</div>
        </CardFooter>
      </Card>
    </div>
  );
}
