"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCheck,
  IconCirclePlus,
  IconCircleMinus,
  IconGitCompare,
  IconLock,
  IconRefresh,
  IconShieldExclamation,
  IconSparkles,
} from "@tabler/icons-react";

import { useAppSelector } from "@/store";
import { useTier } from "@/hooks/useTier";
import { driftApi } from "@/features/drift/api/drift.api";
import type {
  DriftReport,
  BreakingChange,
  NonBreakingChange,
  EndpointDiff,
} from "@/lib/api-client/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ── Method badge colours ──────────────────────────────────────────────────────
const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  POST: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  PATCH: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  DELETE: "bg-rose-500/10 text-rose-400 border-rose-500/20",
};

// ── Change type labels ────────────────────────────────────────────────────────
const CHANGE_TYPE_LABELS: Record<string, string> = {
  endpoint_removed: "Endpoint Removed",
  endpoint_added: "Endpoint Added",
  type_changed: "Type Changed",
  required_field_removed: "Required Field Removed",
  required_field_added: "New Required Field",
  optional_field_added: "Optional Field Added",
  optional_field_removed: "Optional Field Removed",
  field_made_optional: "Field Made Optional",
  description_changed: "Description Changed",
  auth_added: "Auth Added",
  auth_removed: "Auth Removed",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  icon,
  colorClass,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  colorClass: string;
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border bg-card p-5 flex items-center gap-4 shadow-xs transition-all hover:shadow-md ${colorClass}`}
    >
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-background/60 backdrop-blur-sm">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold font-mono tabular-nums">{value}</p>
        <p className="text-xs text-muted-foreground font-medium mt-0.5">{label}</p>
      </div>
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const m = method.toUpperCase();
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-bold font-mono uppercase tracking-wider ${METHOD_COLORS[m] ?? "bg-muted text-muted-foreground border-border"}`}
    >
      {m}
    </span>
  );
}

function EndpointChip({
  ep,
  strikethrough = false,
}: {
  ep: EndpointDiff;
  strikethrough?: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5 py-1.5 px-3 rounded-lg bg-muted/30 border border-border/50 hover:bg-muted/50 transition-colors">
      <MethodBadge method={ep.method} />
      <span
        className={`font-mono text-xs text-foreground truncate ${strikethrough ? "line-through text-muted-foreground" : ""}`}
      >
        {ep.path}
      </span>
      <span className="ml-auto text-[10px] text-muted-foreground font-mono shrink-0">
        {ep.status_code}
      </span>
    </div>
  );
}

function BreakingTable({ changes }: { changes: BreakingChange[] }) {
  if (!changes.length) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-rose-500/20 bg-rose-500/[0.03]">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-rose-500/20 bg-rose-500/10">
              <th className="p-3 font-semibold text-rose-400 whitespace-nowrap">Endpoint</th>
              <th className="p-3 font-semibold text-rose-400 whitespace-nowrap">Change Type</th>
              <th className="p-3 font-semibold text-rose-400 whitespace-nowrap">Field</th>
              <th className="p-3 font-semibold text-rose-400 whitespace-nowrap">Old Value</th>
              <th className="p-3 font-semibold text-rose-400 whitespace-nowrap">New Value</th>
              <th className="p-3 font-semibold text-rose-400">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rose-500/10">
            {changes.map((c, i) => (
              <tr key={i} className="hover:bg-rose-500/5 transition-colors">
                <td className="p-3 font-mono text-[11px] text-foreground/80 whitespace-nowrap max-w-[200px] truncate">
                  {c.endpoint_key}
                </td>
                <td className="p-3 whitespace-nowrap">
                  <span className="inline-flex items-center gap-1 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20 px-2 py-0.5 text-[10px] font-semibold">
                    {CHANGE_TYPE_LABELS[c.change_type] ?? c.change_type}
                  </span>
                </td>
                <td className="p-3 font-mono text-[11px] text-muted-foreground">
                  {c.field_path ?? "—"}
                </td>
                <td className="p-3 font-mono text-[11px] text-rose-400 whitespace-nowrap">
                  {c.old_value != null ? String(c.old_value) : "—"}
                </td>
                <td className="p-3 font-mono text-[11px] text-emerald-400 whitespace-nowrap">
                  {c.new_value != null ? String(c.new_value) : "—"}
                </td>
                <td className="p-3 text-muted-foreground leading-relaxed max-w-[280px]">
                  {c.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NonBreakingTable({ changes }: { changes: NonBreakingChange[] }) {
  if (!changes.length) return null;
  return (
    <div className="overflow-hidden rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03]">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-emerald-500/20 bg-emerald-500/10">
              <th className="p-3 font-semibold text-emerald-400 whitespace-nowrap">Endpoint</th>
              <th className="p-3 font-semibold text-emerald-400 whitespace-nowrap">Change Type</th>
              <th className="p-3 font-semibold text-emerald-400 whitespace-nowrap">Field</th>
              <th className="p-3 font-semibold text-emerald-400">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-emerald-500/10">
            {changes.map((c, i) => (
              <tr key={i} className="hover:bg-emerald-500/5 transition-colors">
                <td className="p-3 font-mono text-[11px] text-foreground/80 whitespace-nowrap max-w-[200px] truncate">
                  {c.endpoint_key}
                </td>
                <td className="p-3 whitespace-nowrap">
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold">
                    {CHANGE_TYPE_LABELS[c.change_type] ?? c.change_type}
                  </span>
                </td>
                <td className="p-3 font-mono text-[11px] text-muted-foreground">
                  {c.field_path ?? "—"}
                </td>
                <td className="p-3 text-muted-foreground leading-relaxed max-w-[360px]">
                  {c.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── PRO gate overlay ──────────────────────────────────────────────────────────

function ProGate() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-6 p-10 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/20">
        <IconLock className="size-7 text-amber-400" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-lg font-bold text-foreground">PRO Feature</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          API Drift Detection is available on the{" "}
          <span className="text-amber-400 font-semibold">PRO</span> plan and above. Upgrade to
          automatically detect breaking API changes between crawls.
        </p>
      </div>
      <Link href="/billing">
        <Button className="gap-2 font-semibold">
          <IconSparkles className="size-4" />
          Upgrade to PRO
        </Button>
      </Link>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({
  icon,
  title,
  count,
  colorClass = "text-foreground",
}: {
  icon: React.ReactNode;
  title: string;
  count: number;
  colorClass?: string;
}) {
  return (
    <div className="flex items-center gap-2.5 mb-3">
      <span className={colorClass}>{icon}</span>
      <h3 className={`text-sm font-semibold ${colorClass}`}>{title}</h3>
      <span className="ml-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono text-muted-foreground">
        {count}
      </span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DriftReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const user = useAppSelector((s) => s.auth.user);
  const { hasTierAccess } = useTier();

  const compareCrawlId = params.id as string;
  const baseCrawlId = searchParams.get("base") ?? undefined;

  const [report, setReport] = useState<DriftReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    if (!user?.id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await driftApi.getDriftReport(user.id, compareCrawlId, baseCrawlId);
      setReport(data);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load drift report.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [user?.id, compareCrawlId, baseCrawlId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // ── Render states ───────────────────────────────────────────────────────────

  if (!hasTierAccess("PRO")) return <ProGate />;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-muted-foreground">
        <div className="size-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <span className="text-sm">Analysing API drift…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-4 p-8 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
          <IconAlertTriangle className="size-6 text-destructive" />
        </div>
        <div className="space-y-1 max-w-sm">
          <p className="text-sm font-semibold text-foreground">Failed to load drift report</p>
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchReport} className="gap-2">
          <IconRefresh className="size-4" />
          Retry
        </Button>
      </div>
    );
  }

  if (!report) return null;

  const generatedAt = new Date(report.generated_at).toLocaleString();
  const shortId = (id: string) => `${id.slice(0, 8)}…`;

  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-y-auto">
      {/* ── Hero bar ────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-10 border-b border-border/50 bg-background/95 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <IconArrowLeft className="size-3.5" />
            Back
          </button>

          <div className="flex items-center gap-2 ml-2">
            <IconGitCompare className="size-5 text-primary" />
            <h1 className="text-base font-bold text-foreground">API Drift Report</h1>
          </div>

          {report.has_breaking_changes ? (
            <Badge variant="destructive" className="gap-1.5 text-xs font-semibold">
              <IconShieldExclamation className="size-3" />
              Breaking Changes
            </Badge>
          ) : (
            <Badge className="gap-1.5 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
              <IconCheck className="size-3" />
              No Breaking Changes
            </Badge>
          )}

          <div className="ml-auto flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
            <span>
              base:{" "}
              <span className="text-foreground/80" title={report.base_crawl_id}>
                {shortId(report.base_crawl_id)}
              </span>
            </span>
            <span className="text-border">→</span>
            <span>
              compare:{" "}
              <span className="text-foreground/80" title={report.compare_crawl_id}>
                {shortId(report.compare_crawl_id)}
              </span>
            </span>
            <span className="text-border/60">·</span>
            <span>{generatedAt}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-8">
        {/* ── Summary cards ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard
            label="Breaking Changes"
            value={report.summary.breaking_count}
            icon={<IconShieldExclamation className="size-5 text-rose-400" />}
            colorClass={
              report.summary.breaking_count > 0
                ? "border-rose-500/25 bg-rose-500/[0.04]"
                : "border-border"
            }
          />
          <StatCard
            label="Non-Breaking Changes"
            value={report.summary.non_breaking_count}
            icon={<IconCheck className="size-5 text-emerald-400" />}
            colorClass="border-border"
          />
          <StatCard
            label="Endpoints Added"
            value={report.summary.added_count}
            icon={<IconCirclePlus className="size-5 text-blue-400" />}
            colorClass="border-border"
          />
          <StatCard
            label="Endpoints Removed"
            value={report.summary.removed_count}
            icon={<IconCircleMinus className="size-5 text-amber-400" />}
            colorClass="border-border"
          />
        </div>

        {/* ── Breaking changes ───────────────────────────────────────────── */}
        {report.breaking_changes.length > 0 && (
          <section>
            <SectionHeader
              icon={<IconShieldExclamation className="size-4" />}
              title="Breaking Changes"
              count={report.breaking_changes.length}
              colorClass="text-rose-400"
            />
            <BreakingTable changes={report.breaking_changes} />
          </section>
        )}

        {/* ── Non-breaking changes ───────────────────────────────────────── */}
        {report.non_breaking_changes.length > 0 && (
          <section>
            <SectionHeader
              icon={<IconCheck className="size-4" />}
              title="Non-Breaking Changes"
              count={report.non_breaking_changes.length}
              colorClass="text-emerald-400"
            />
            <NonBreakingTable changes={report.non_breaking_changes} />
          </section>
        )}

        {/* ── Added endpoints ────────────────────────────────────────────── */}
        {report.added_endpoints.length > 0 && (
          <section>
            <SectionHeader
              icon={<IconCirclePlus className="size-4" />}
              title="Added Endpoints"
              count={report.added_endpoints.length}
              colorClass="text-blue-400"
            />
            <div className="grid gap-1.5 sm:grid-cols-2">
              {report.added_endpoints.map((ep) => (
                <EndpointChip key={ep.endpoint_key} ep={ep} />
              ))}
            </div>
          </section>
        )}

        {/* ── Removed endpoints ──────────────────────────────────────────── */}
        {report.removed_endpoints.length > 0 && (
          <section>
            <SectionHeader
              icon={<IconCircleMinus className="size-4" />}
              title="Removed Endpoints"
              count={report.removed_endpoints.length}
              colorClass="text-amber-400"
            />
            <div className="grid gap-1.5 sm:grid-cols-2">
              {report.removed_endpoints.map((ep) => (
                <EndpointChip key={ep.endpoint_key} ep={ep} strikethrough />
              ))}
            </div>
          </section>
        )}

        {/* ── No changes at all ──────────────────────────────────────────── */}
        {report.breaking_changes.length === 0 &&
          report.non_breaking_changes.length === 0 &&
          report.added_endpoints.length === 0 &&
          report.removed_endpoints.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
                <IconCheck className="size-6 text-emerald-400" />
              </div>
              <p className="text-sm font-semibold text-foreground">No API changes detected</p>
              <p className="text-xs text-muted-foreground max-w-xs">
                The two crawls produced identical endpoint schemas. Your API is stable.
              </p>
            </div>
          )}

        {/* ── Footer metadata ────────────────────────────────────────────── */}
        <div className="border-t border-border/40 pt-6 flex flex-wrap gap-4 text-[11px] text-muted-foreground font-mono">
          <span>
            Base crawl: <span className="text-foreground/70">{report.base_crawl_id}</span>
          </span>
          <span>
            Compare crawl: <span className="text-foreground/70">{report.compare_crawl_id}</span>
          </span>
          <span>
            Base endpoints: <span className="text-foreground/70">{report.summary.total_endpoints_base}</span>
          </span>
          <span>
            Compare endpoints:{" "}
            <span className="text-foreground/70">{report.summary.total_endpoints_compare}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
