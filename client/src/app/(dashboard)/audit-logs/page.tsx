"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
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

  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  const stats = useMemo(() => {
    const crawlEvents = logs.filter((l) => l.action.startsWith("crawl")).length;
    const authEvents = logs.filter((l) => l.action.startsWith("auth") || l.action.startsWith("user")).length;
    const exportEvents = logs.filter((l) => l.action.startsWith("export") || l.action.startsWith("report")).length;
    return { crawlEvents, authEvents, exportEvents };
  }, [logs]);

  const getActionBadge = (action: string) => {
    if (action.startsWith("crawl")) {
      return (
        <Badge variant="outline" className="text-[10px] font-mono font-bold border-emerald-500/40 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 uppercase">
          {action}
        </Badge>
      );
    }
    if (action.startsWith("auth")) {
      return (
        <Badge variant="outline" className="text-[10px] font-mono font-bold border-purple-500/40 text-purple-400 bg-purple-500/10 px-2 py-0.5 uppercase">
          {action}
        </Badge>
      );
    }
    if (action.startsWith("export") || action.startsWith("report")) {
      return (
        <Badge variant="outline" className="text-[10px] font-mono font-bold border-blue-500/40 text-blue-400 bg-blue-500/10 px-2 py-0.5 uppercase">
          {action}
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-[10px] font-mono font-bold border-amber-500/40 text-amber-400 bg-amber-500/10 px-2 py-0.5 uppercase">
        {action}
      </Badge>
    );
  };

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto w-full font-sans pb-28">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 shadow-xs">
            <IconShieldLock className="size-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              Enterprise Security Audit Trail
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Immutable SOC2 Type II & ISO 27001 audit ledger tracking administrative actions, automated scans, and token exports.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV} className="text-xs gap-1.5 h-8">
            <IconDownload className="size-3.5" /> Export CSV
          </Button>
          <Button variant="outline" size="sm" onClick={loadLogs} disabled={loading} className="text-xs gap-1.5 h-8">
            <IconRefresh className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Total Audit Records</div>
          <div className="text-2xl font-extrabold font-mono text-foreground">{total}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Logged event operations</div>
        </div>
        <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 shadow-xs">
          <div className="text-[11px] text-emerald-500 font-mono uppercase mb-1">Crawl Executions</div>
          <div className="text-2xl font-extrabold font-mono text-emerald-400">{stats.crawlEvents}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Agent exploration events</div>
        </div>
        <div className="p-4 rounded-2xl border border-purple-500/20 bg-purple-500/5 shadow-xs">
          <div className="text-[11px] text-purple-400 font-mono uppercase mb-1">Auth & Profile Events</div>
          <div className="text-2xl font-extrabold font-mono text-purple-400">{stats.authEvents}</div>
          <div className="text-[11px] text-muted-foreground mt-1">Credential verifications</div>
        </div>
        <div className="p-4 rounded-2xl border border-border/60 bg-card shadow-xs">
          <div className="text-[11px] text-muted-foreground font-mono uppercase mb-1">Compliance Policy</div>
          <div className="text-2xl font-extrabold font-mono text-primary">365 Days</div>
          <div className="text-[11px] text-muted-foreground mt-1">Retention lock active</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center gap-3 flex-wrap bg-card p-3 rounded-2xl border border-border/60 shadow-xs">
        <div className="relative flex-1 min-w-[220px]">
          <IconSearch className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by action, target ID, IP, or user..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 text-xs h-8 bg-muted/20 border-border/60"
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
        <div className="p-3.5 border-b border-border/40 bg-muted/20 flex items-center justify-between text-xs font-mono text-muted-foreground">
          <span>Showing {filteredLogs.length} of {total} events</span>
          <span>SOC2 Type II Immutable Log</span>
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
              <div
                key={log.id}
                className="p-4 hover:bg-muted/20 transition-colors flex items-center justify-between gap-4 flex-wrap"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    {getActionBadge(log.action)}
                    <span className="text-foreground font-bold truncate max-w-sm">{log.target_id || "system"}</span>
                    {log.ip_address && (
                      <span className="text-muted-foreground text-[11px] bg-muted/40 px-1.5 py-0.5 rounded border border-border/40">
                        {log.ip_address}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-3">
                    <span>Actor: <strong className="text-foreground">{log.user_id.slice(0, 8)}…</strong></span>
                    <span>&bull;</span>
                    <span>{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedLog(log)}
                      className="text-[11px] h-7 gap-1 font-mono text-muted-foreground hover:text-foreground"
                    >
                      <IconFileText className="size-3" /> Metadata JSON
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata Detail Dialog */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="max-w-xl w-full p-6 rounded-2xl bg-card border border-border shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border/40 pb-3">
              <div className="space-y-0.5">
                <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
                  <IconShieldLock className="size-4 text-primary" />
                  Audit Event Metadata
                </h3>
                <p className="text-xs font-mono text-muted-foreground">
                  Action: {selectedLog.action} &bull; ID: {selectedLog.id}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setSelectedLog(null)} className="h-7 w-7 p-0">
                ✕
              </Button>
            </div>

            <pre className="p-4 rounded-xl bg-[#111318] text-emerald-400 font-mono text-xs overflow-x-auto max-h-80 leading-relaxed border border-border/60">
              {JSON.stringify(selectedLog.metadata, null, 2)}
            </pre>

            <div className="flex justify-end">
              <Button size="sm" onClick={() => setSelectedLog(null)} className="text-xs">
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
