"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  IconFileText,
  IconRefresh,
  IconShieldLock,
  IconDownload,
  IconSearch,
  IconClock,
  IconUser,
  IconWorld,
  IconActivity,
} from "@tabler/icons-react";
import { toast } from "sonner";
import { auditApi, AuditLogItem } from "@/features/audit-logs/api/audit.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await auditApi.getAuditLogs({
        limit: 50,
        action: actionFilter || undefined,
      });
      setLogs(res.audit_logs || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      if (err.response?.status === 403) {
        toast.error("Enterprise tier required to access enterprise audit logs.");
      } else {
        toast.error("Failed to load audit trail.");
      }
    } finally {
      setLoading(false);
    }
  }, [actionFilter]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      (log.target_id && log.target_id.toLowerCase().includes(q)) ||
      (log.ip_address && log.ip_address.toLowerCase().includes(q)) ||
      (log.user_id && log.user_id.toLowerCase().includes(q))
    );
  });

  const handleExportCSV = () => {
    if (logs.length === 0) return;
    const headers = ["ID", "Timestamp", "Actor User ID", "Action", "Target ID", "IP Address", "Metadata"];
    const rows = logs.map((l) => [
      l.id,
      l.created_at,
      l.user_id,
      l.action,
      l.target_id || "",
      l.ip_address || "",
      JSON.stringify(l.metadata || {}),
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Exported audit log CSV!");
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-y-auto p-6 space-y-6 max-w-7xl mx-auto w-full font-sans">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20">
            <IconShieldLock className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Enterprise Security Audit Trail</h1>
            <p className="text-xs text-muted-foreground">
              Immutable SOC2 & ISO 27001 audit ledger tracking administrative, authentication, and crawl actions.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV} className="text-xs gap-1.5">
            <IconDownload className="size-3.5" /> Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={loadLogs} disabled={loading} className="text-xs gap-1.5">
            <IconRefresh className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <IconSearch className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by action, target ID, IP, or user..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-xs"
          />
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {["", "crawl.create", "export.download", "auth_profile.test", "drift_webhook.trigger"].map((act) => (
            <Button
              key={act}
              size="sm"
              variant={actionFilter === act ? "default" : "outline"}
              onClick={() => setActionFilter(act)}
              className="text-[11px] h-8 px-2.5 font-mono"
            >
              {act === "" ? "All Actions" : act}
            </Button>
          ))}
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="border border-border/60 rounded-2xl bg-card shadow-xs overflow-hidden">
        <div className="p-3 border-b border-border/40 bg-muted/20 flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Showing {filteredLogs.length} of {total} events</span>
          <span>Retention: 365 Days (Enterprise)</span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-xs text-muted-foreground font-mono animate-pulse">
            Loading enterprise audit ledger records…
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-xs text-muted-foreground font-mono">
            No audit records match the current filter.
          </div>
        ) : (
          <div className="divide-y divide-border/40 font-mono text-xs">
            {filteredLogs.map((log) => (
              <div key={log.id} className="p-4 hover:bg-muted/10 transition-colors flex items-center justify-between gap-4 flex-wrap">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] uppercase font-bold border-primary/30 text-primary bg-primary/5 px-1.5 py-0">
                      {log.action}
                    </Badge>
                    <span className="text-foreground font-bold">{log.target_id || "system"}</span>
                    {log.ip_address && (
                      <span className="text-muted-foreground text-[11px]">({log.ip_address})</span>
                    )}
                  </div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-3">
                    <span>Actor: {log.user_id.slice(0, 8)}…</span>
                    <span>&bull;</span>
                    <span>{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                </div>

                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <div className="bg-muted/40 p-2 rounded-lg border border-border/40 text-[10px] text-muted-foreground max-w-sm truncate">
                    {JSON.stringify(log.metadata)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
