"use client";

import React, { useState } from "react";
import { ShieldAlertIcon, CheckCircle2Icon, XCircleIcon, Loader2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface ApprovalAction {
  method: string;
  url: string;
  description: string;
}

export interface ApprovalCardProps {
  approvalId: string;
  action: ApprovalAction;
  onApprove?: (approvalId: string, action: ApprovalAction) => void;
  onReject?: (approvalId: string, action: ApprovalAction) => void;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  approvalId,
  action,
  onApprove,
  onReject,
}) => {
  const [status, setStatus] = useState<"pending" | "approved" | "rejected">("pending");

  const handleApprove = () => {
    setStatus("approved");
    onApprove?.(approvalId, action);
  };

  const handleReject = () => {
    setStatus("rejected");
    onReject?.(approvalId, action);
  };

  return (
    <div className="my-3 rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 shadow-sm backdrop-blur-xs">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500 border border-amber-500/20 shrink-0">
          <ShieldAlertIcon className="size-5" />
        </div>

        <div className="flex-1 space-y-1.5 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-500">
              Security Guardrail: Human Approval Required
            </span>
            <span className="text-[11px] font-mono text-muted-foreground">
              {action.method}
            </span>
          </div>

          <p className="text-xs text-foreground font-medium">
            {action.description || "The agent is requesting permission to execute a mutable or security action on a live target."}
          </p>

          <div className="p-2 rounded-lg bg-background/80 border border-border/60 text-xs font-mono text-muted-foreground break-all">
            <span className="text-amber-500 font-bold">{action.method}</span> {action.url}
          </div>

          {status === "pending" ? (
            <div className="flex items-center gap-2 pt-2">
              <Button
                size="sm"
                variant="default"
                onClick={handleApprove}
                className="bg-amber-600 hover:bg-amber-700 text-white text-xs h-8 px-3 rounded-xl gap-1.5"
              >
                <CheckCircle2Icon className="size-3.5" />
                Approve &amp; Execute
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleReject}
                className="text-xs h-8 px-3 rounded-xl border-border/60 hover:bg-muted text-muted-foreground hover:text-foreground gap-1.5"
              >
                <XCircleIcon className="size-3.5" />
                Skip Action
              </Button>
            </div>
          ) : status === "approved" ? (
            <div className="flex items-center gap-1.5 pt-1 text-xs text-emerald-500 font-medium">
              <CheckCircle2Icon className="size-3.5" />
              Action Approved &mdash; Executing probe...
            </div>
          ) : (
            <div className="flex items-center gap-1.5 pt-1 text-xs text-muted-foreground font-medium">
              <XCircleIcon className="size-3.5" />
              Action Skipped by user.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
