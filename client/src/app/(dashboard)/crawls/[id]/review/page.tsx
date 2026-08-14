"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  IconArrowLeft,
  IconCheck,
  IconAlertTriangle,
  IconRefresh,
  IconSparkles,
  IconFileCode,
  IconAdjustments,
  IconEyeOff,
  IconEye,
  IconDeviceFloppy,
  IconCode,
  IconListDetails,
  IconCircleCheck,
  IconDownload,
  IconGitCompare,
  IconX,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react";
import { toast } from "sonner";

import { reviewApi } from "@/features/review/api/review.api";
import { crawlsApi } from "@/features/crawls/api/crawls.api";
import type { EndpointReviewItem, CrawlSession } from "@/lib/api-client/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// ── Method badge styles ───────────────────────────────────────────────────────
const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  POST: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  PATCH: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  DELETE: "bg-rose-500/10 text-rose-400 border-rose-500/20",
};

// ── Confidence rating helpers ─────────────────────────────────────────────────
function getConfidenceStyle(confidence: number) {
  if (confidence < 0.5) {
    return {
      label: "Low Confidence",
      color: "bg-rose-500/10 text-rose-400 border-rose-500/25",
      indicator: "bg-rose-500",
      tier: "low",
    };
  }
  if (confidence < 0.75) {
    return {
      label: "Medium Confidence",
      color: "bg-amber-500/10 text-amber-400 border-amber-500/25",
      indicator: "bg-amber-500",
      tier: "medium",
    };
  }
  return {
    label: "High Confidence",
    color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
    indicator: "bg-emerald-500",
    tier: "high",
  };
}

// ── Property row editor for structured schema view ────────────────────────────
interface SchemaProperty {
  name: string;
  type: string;
  required: boolean;
  description?: string;
}

function extractPropertiesFromSchema(schema: Record<string, unknown> | null): SchemaProperty[] {
  if (!schema || typeof schema !== "object") return [];
  const props = (schema.properties as Record<string, Record<string, unknown>>) || {};
  const requiredList = Array.isArray(schema.required) ? (schema.required as string[]) : [];

  return Object.entries(props).map(([key, val]) => ({
    name: key,
    type: typeof val?.type === "string" ? val.type : "string",
    required: requiredList.includes(key),
    description: typeof val?.description === "string" ? val.description : "",
  }));
}

function buildSchemaFromProperties(
  properties: SchemaProperty[],
  originalSchema: Record<string, unknown> | null
): Record<string, unknown> {
  const propsObj: Record<string, { type: string; description?: string }> = {};
  const reqList: string[] = [];

  properties.forEach((p) => {
    if (!p.name.trim()) return;
    propsObj[p.name] = {
      type: p.type || "string",
      ...(p.description ? { description: p.description } : {}),
    };
    if (p.required) {
      reqList.push(p.name);
    }
  });

  return {
    ...(originalSchema || {}),
    type: "object",
    properties: propsObj,
    ...(reqList.length > 0 ? { required: reqList } : {}),
  };
}

export default function CrawlReviewPage() {
  const params = useParams();
  const router = useRouter();
  const crawlId = params.id as string;

  const [session, setSession] = useState<CrawlSession | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit states per endpoint: { [key]: { rawJson: string, props: SchemaProperty[], isExcluded: boolean, mode: "fields" | "json", isDirty: boolean } }
  const [editStates, setEditStates] = useState<
    Record<
      string,
      {
        rawJson: string;
        jsonError: string | null;
        props: SchemaProperty[];
        isExcluded: boolean;
        mode: "fields" | "json";
        isDirty: boolean;
        saving: boolean;
      }
    >
  >({});

  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [bulkThreshold, setBulkThreshold] = useState<number>(0.75);
  const [approving, setApproving] = useState(false);
  const [approveSuccessDialog, setApproveSuccessDialog] = useState<{
    open: boolean;
    capturedCount: number;
    excludedCount: number;
  }>({ open: false, capturedCount: 0, excludedCount: 0 });

  // ── Load data ───────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionData, endpointsData] = await Promise.all([
        crawlsApi.getCrawlById(crawlId).catch(() => null),
        reviewApi.listEndpoints(crawlId),
      ]);

      if (sessionData) setSession(sessionData);
      setEndpoints(endpointsData);

      // Initialize edit states
      const initialEdits: typeof editStates = {};
      const autoExpandKeys = new Set<string>();

      endpointsData.forEach((ep) => {
        const activeSchema = ep.reviewed_schema || ep.schema_json || {};
        const props = extractPropertiesFromSchema(activeSchema);
        initialEdits[ep.endpoint_key] = {
          rawJson: JSON.stringify(activeSchema, null, 2),
          jsonError: null,
          props,
          isExcluded: ep.is_excluded,
          mode: "fields",
          isDirty: false,
          saving: false,
        };

        // Automatically expand low confidence endpoints (<0.6) for immediate review
        if (ep.confidence < 0.6) {
          autoExpandKeys.add(ep.endpoint_key);
        }
      });

      setEditStates(initialEdits);
      setExpandedKeys(autoExpandKeys);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load crawl endpoints for review.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [crawlId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Summary metrics ─────────────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const total = endpoints.length;
    const low = endpoints.filter((e) => e.confidence < 0.5).length;
    const med = endpoints.filter((e) => e.confidence >= 0.5 && e.confidence < 0.75).length;
    const high = endpoints.filter((e) => e.confidence >= 0.75).length;
    const excluded = Object.values(editStates).filter((s) => s.isExcluded).length;
    const modified = Object.values(editStates).filter((s) => s.isDirty).length;

    return { total, low, med, high, excluded, included: total - excluded, modified };
  }, [endpoints, editStates]);

  // ── Toggle endpoint expansion ───────────────────────────────────────────────
  const toggleExpand = (key: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // ── Toggle Exclude / Include ────────────────────────────────────────────────
  const handleToggleExclude = async (key: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const current = editStates[key];
    if (!current) return;

    const newExcluded = !current.isExcluded;

    setEditStates((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        isExcluded: newExcluded,
        isDirty: true,
      },
    }));

    try {
      await reviewApi.patchEndpoint(crawlId, key, { is_excluded: newExcluded });
      toast.success(newExcluded ? `Excluded '${key}' from export` : `Included '${key}' in export`);
    } catch (err: unknown) {
      toast.error("Failed to update exclusion status");
      // Revert on error
      setEditStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], isExcluded: !newExcluded },
      }));
    }
  };

  // ── Field Property Changes ──────────────────────────────────────────────────
  const handlePropertyChange = (
    key: string,
    index: number,
    field: keyof SchemaProperty,
    val: unknown
  ) => {
    setEditStates((prev) => {
      const state = prev[key];
      if (!state) return prev;
      const updatedProps = [...state.props];
      updatedProps[index] = { ...updatedProps[index], [field]: val };

      const ep = endpoints.find((e) => e.endpoint_key === key);
      const originalSchema = ep?.reviewed_schema || ep?.schema_json || {};
      const newSchema = buildSchemaFromProperties(updatedProps, originalSchema);

      return {
        ...prev,
        [key]: {
          ...state,
          props: updatedProps,
          rawJson: JSON.stringify(newSchema, null, 2),
          jsonError: null,
          isDirty: true,
        },
      };
    });
  };

  const handleAddProperty = (key: string) => {
    setEditStates((prev) => {
      const state = prev[key];
      if (!state) return prev;
      const updatedProps = [
        ...state.props,
        { name: `field_${state.props.length + 1}`, type: "string", required: false },
      ];

      const ep = endpoints.find((e) => e.endpoint_key === key);
      const originalSchema = ep?.reviewed_schema || ep?.schema_json || {};
      const newSchema = buildSchemaFromProperties(updatedProps, originalSchema);

      return {
        ...prev,
        [key]: {
          ...state,
          props: updatedProps,
          rawJson: JSON.stringify(newSchema, null, 2),
          isDirty: true,
        },
      };
    });
  };

  const handleRemoveProperty = (key: string, index: number) => {
    setEditStates((prev) => {
      const state = prev[key];
      if (!state) return prev;
      const updatedProps = state.props.filter((_, i) => i !== index);

      const ep = endpoints.find((e) => e.endpoint_key === key);
      const originalSchema = ep?.reviewed_schema || ep?.schema_json || {};
      const newSchema = buildSchemaFromProperties(updatedProps, originalSchema);

      return {
        ...prev,
        [key]: {
          ...state,
          props: updatedProps,
          rawJson: JSON.stringify(newSchema, null, 2),
          isDirty: true,
        },
      };
    });
  };

  // ── JSON editor change ──────────────────────────────────────────────────────
  const handleRawJsonChange = (key: string, val: string) => {
    setEditStates((prev) => {
      const state = prev[key];
      if (!state) return prev;

      let parsedProps = state.props;
      let jsonErr: string | null = null;

      try {
        const parsed = JSON.parse(val);
        if (typeof parsed === "object" && parsed !== null) {
          parsedProps = extractPropertiesFromSchema(parsed);
        }
      } catch (err: unknown) {
        jsonErr = (err as Error).message;
      }

      return {
        ...prev,
        [key]: {
          ...state,
          rawJson: val,
          jsonError: jsonErr,
          props: parsedProps,
          isDirty: true,
        },
      };
    });
  };

  // ── Save single endpoint ────────────────────────────────────────────────────
  const handleSaveEndpoint = async (key: string) => {
    const state = editStates[key];
    if (!state) return;

    if (state.jsonError) {
      toast.error(`Invalid JSON in '${key}': ${state.jsonError}`);
      return;
    }

    let parsedSchema: Record<string, unknown>;
    try {
      parsedSchema = JSON.parse(state.rawJson);
    } catch {
      toast.error(`Cannot save invalid JSON schema for ${key}`);
      return;
    }

    setEditStates((prev) => ({
      ...prev,
      [key]: { ...prev[key], saving: true },
    }));

    try {
      const updated = await reviewApi.patchEndpoint(crawlId, key, {
        schema: parsedSchema,
        is_excluded: state.isExcluded,
      });

      // Update endpoints list with the new reviewed schema
      setEndpoints((prev) =>
        prev.map((e) => (e.endpoint_key === key ? { ...e, ...updated, has_review: true } : e))
      );

      setEditStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], isDirty: false, saving: false },
      }));

      toast.success(`Schema updated for ${key}`);
    } catch (err: unknown) {
      toast.error(`Failed to save schema for ${key}`);
      setEditStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], saving: false },
      }));
    }
  };

  // ── Bulk threshold auto-exclude ─────────────────────────────────────────────
  const handleBulkExcludeBelowThreshold = () => {
    let count = 0;
    const newEdits = { ...editStates };

    endpoints.forEach((ep) => {
      if (ep.confidence < bulkThreshold && !newEdits[ep.endpoint_key]?.isExcluded) {
        newEdits[ep.endpoint_key] = {
          ...newEdits[ep.endpoint_key],
          isExcluded: true,
          isDirty: true,
        };
        count++;
      }
    });

    setEditStates(newEdits);
    toast.info(`Marked ${count} endpoint(s) below ${(bulkThreshold * 100).toFixed(0)}% confidence as excluded`);
  };

  // ── Approve & Export ────────────────────────────────────────────────────────
  const handleApprove = async () => {
    if (metrics.included <= 0) {
      toast.error("At least one endpoint must be included in export.");
      return;
    }

    setApproving(true);
    try {
      // Save any pending dirty edits first
      const dirtyKeys = Object.entries(editStates)
        .filter(([, s]) => s.isDirty)
        .map(([k]) => k);

      for (const key of dirtyKeys) {
        const state = editStates[key];
        if (!state.jsonError) {
          try {
            const parsed = JSON.parse(state.rawJson);
            await reviewApi.patchEndpoint(crawlId, key, {
              schema: parsed,
              is_excluded: state.isExcluded,
            });
          } catch {}
        }
      }

      const res = await reviewApi.approveCrawl(crawlId);
      setApproveSuccessDialog({
        open: true,
        capturedCount: res.captured_count,
        excludedCount: res.excluded_count,
      });
      toast.success("Crawl approved! OpenAPI & Postman specifications generated.");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to approve crawl.";
      toast.error(msg);
    } finally {
      setApproving(false);
    }
  };

  // ── Loading & Error states ──────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-muted-foreground min-h-[60vh]">
        <div className="size-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        <span className="text-sm font-mono">Loading captured endpoints for review…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-4 p-8 text-center min-h-[60vh]">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 border border-destructive/20">
          <IconAlertTriangle className="size-6 text-destructive" />
        </div>
        <div className="space-y-1 max-w-sm">
          <p className="text-sm font-semibold text-foreground">Failed to load endpoints</p>
          <p className="text-xs text-muted-foreground">{error}</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} className="gap-2">
          <IconRefresh className="size-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-y-auto pb-24">
      {/* ── Top Header ────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 border-b border-border/50 bg-background/95 backdrop-blur-md px-6 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <IconArrowLeft className="size-4" />
              Back
            </button>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-2">
              <IconSparkles className="size-5 text-primary" />
              <h1 className="text-base font-bold text-foreground">Human-in-the-Loop Schema Review</h1>
            </div>
            {session?.status === "pending_review" ? (
              <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 text-xs font-mono">
                pending_review
              </Badge>
            ) : (
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 text-xs font-mono">
                {session?.status || "active"}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
            <span className="truncate max-w-[280px]">{session?.target_url || "Target Website"}</span>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
        {/* ── Metrics Cards ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-foreground">{metrics.total}</p>
            <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Total Endpoints</p>
          </div>
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/[0.04] p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-rose-400">{metrics.low}</p>
            <p className="text-[11px] text-rose-400/80 font-medium mt-0.5">Low Confidence (&lt;50%)</p>
          </div>
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-amber-400">{metrics.med}</p>
            <p className="text-[11px] text-amber-400/80 font-medium mt-0.5">Medium (50-75%)</p>
          </div>
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-emerald-400">{metrics.high}</p>
            <p className="text-[11px] text-emerald-400/80 font-medium mt-0.5">High Confidence (&ge;75%)</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-primary">{metrics.included}</p>
            <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Included in Spec</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
            <p className="text-xl font-bold font-mono text-muted-foreground">{metrics.excluded}</p>
            <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Excluded</p>
          </div>
        </div>

        {/* ── Confidence Distribution & Bulk Threshold Controls ────────────── */}
        <div className="rounded-2xl border border-border bg-card p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <IconAdjustments className="size-4 text-primary" />
              <span className="text-xs font-semibold text-foreground">Confidence Threshold Filter</span>
              <span className="text-[11px] text-muted-foreground">
                Endpoints are sorted with lowest confidence first so uncertain schemas get immediate scrutiny.
              </span>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-muted-foreground">
                  Threshold: {(bulkThreshold * 100).toFixed(0)}%
                </span>
                <input
                  type="range"
                  min="0.1"
                  max="0.95"
                  step="0.05"
                  value={bulkThreshold}
                  onChange={(e) => setBulkThreshold(parseFloat(e.target.value))}
                  className="w-24 h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleBulkExcludeBelowThreshold}
                className="text-xs font-mono gap-1.5 h-7"
              >
                <IconEyeOff className="size-3.5 text-muted-foreground" />
                Exclude &lt;{(bulkThreshold * 100).toFixed(0)}%
              </Button>
            </div>
          </div>

          {/* Mini confidence visual bar */}
          <div className="w-full h-2 rounded-full bg-muted overflow-hidden flex">
            <div
              className="bg-rose-500 transition-all"
              style={{ width: `${metrics.total ? (metrics.low / metrics.total) * 100 : 0}%` }}
              title={`Low: ${metrics.low}`}
            />
            <div
              className="bg-amber-500 transition-all"
              style={{ width: `${metrics.total ? (metrics.med / metrics.total) * 100 : 0}%` }}
              title={`Medium: ${metrics.med}`}
            />
            <div
              className="bg-emerald-500 transition-all"
              style={{ width: `${metrics.total ? (metrics.high / metrics.total) * 100 : 0}%` }}
              title={`High: ${metrics.high}`}
            />
          </div>
        </div>

        {/* ── Endpoints Review List ─────────────────────────────────────────── */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span>Captured Endpoints ({endpoints.length})</span>
            <div className="flex gap-2">
              <button
                onClick={() => setExpandedKeys(new Set(endpoints.map((e) => e.endpoint_key)))}
                className="hover:text-foreground text-[11px] underline"
              >
                Expand All
              </button>
              <span>·</span>
              <button
                onClick={() => setExpandedKeys(new Set())}
                className="hover:text-foreground text-[11px] underline"
              >
                Collapse All
              </button>
            </div>
          </div>

          {endpoints.map((ep, idx) => {
            const key = ep.endpoint_key;
            const editState = editStates[key] || {
              rawJson: "{}",
              jsonError: null,
              props: [],
              isExcluded: false,
              mode: "fields",
              isDirty: false,
              saving: false,
            };

            const isExpanded = expandedKeys.has(key);
            const confStyle = getConfidenceStyle(ep.confidence);
            const m = ep.method.toUpperCase();

            return (
              <div
                key={key}
                className={`rounded-2xl border transition-all ${
                  editState.isExcluded
                    ? "border-border/40 bg-muted/20 opacity-70"
                    : editState.isDirty
                    ? "border-primary/40 bg-primary/[0.02]"
                    : "border-border bg-card"
                }`}
              >
                {/* ── Endpoint Header Row ──────────────────────────────────── */}
                <div
                  onClick={() => toggleExpand(key)}
                  className="flex items-center gap-3 p-4 cursor-pointer select-none flex-wrap"
                >
                  <span className="font-mono text-xs text-muted-foreground w-6 text-right">
                    #{idx + 1}
                  </span>

                  <span
                    className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-[10px] font-bold font-mono uppercase tracking-wider ${
                      METHOD_COLORS[m] ?? "bg-muted text-muted-foreground border-border"
                    }`}
                  >
                    {m}
                  </span>

                  <span
                    className={`font-mono text-xs font-semibold text-foreground truncate max-w-md ${
                      editState.isExcluded ? "line-through text-muted-foreground" : ""
                    }`}
                  >
                    {ep.path}
                  </span>

                  <span className="text-[10px] font-mono text-muted-foreground border border-border/60 rounded px-1.5 py-0.5">
                    HTTP {ep.status_code}
                  </span>

                  {/* Confidence score badge */}
                  <div
                    className={`ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-mono font-medium ${confStyle.color}`}
                  >
                    <span className={`size-1.5 rounded-full ${confStyle.indicator}`} />
                    <span>{(ep.confidence * 100).toFixed(0)}%</span>
                  </div>

                  {/* Example count */}
                  <span className="text-[10px] font-mono text-muted-foreground hidden sm:inline">
                    {ep.example_count} example{ep.example_count > 1 ? "s" : ""}
                  </span>

                  {/* Review / Override badge */}
                  {ep.has_review && (
                    <Badge variant="outline" className="text-[10px] font-mono border-primary/40 text-primary">
                      Reviewed
                    </Badge>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 ml-2" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant={editState.isExcluded ? "secondary" : "outline"}
                      size="sm"
                      onClick={(e) => handleToggleExclude(key, e)}
                      className="h-7 text-xs px-2.5 gap-1"
                      title={editState.isExcluded ? "Include in export" : "Exclude from export"}
                    >
                      {editState.isExcluded ? (
                        <>
                          <IconEye className="size-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Include</span>
                        </>
                      ) : (
                        <>
                          <IconEyeOff className="size-3.5 text-muted-foreground" />
                          <span>Exclude</span>
                        </>
                      )}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleExpand(key)}
                      className="h-7 text-xs px-2 text-muted-foreground"
                    >
                      {isExpanded ? "Collapse" : "Edit Schema"}
                    </Button>
                  </div>
                </div>

                {/* ── Expanded Schema Editor ───────────────────────────────── */}
                {isExpanded && (
                  <div className="border-t border-border/50 p-4 space-y-4 bg-muted/[0.04]">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Button
                          variant={editState.mode === "fields" ? "default" : "outline"}
                          size="sm"
                          onClick={() =>
                            setEditStates((prev) => ({
                              ...prev,
                              [key]: { ...prev[key], mode: "fields" },
                            }))
                          }
                          className="h-7 text-xs gap-1"
                        >
                          <IconListDetails className="size-3.5" />
                          Structured Fields
                        </Button>
                        <Button
                          variant={editState.mode === "json" ? "default" : "outline"}
                          size="sm"
                          onClick={() =>
                            setEditStates((prev) => ({
                              ...prev,
                              [key]: { ...prev[key], mode: "json" },
                            }))
                          }
                          className="h-7 text-xs gap-1"
                        >
                          <IconCode className="size-3.5" />
                          Raw JSON Schema
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        {editState.isDirty && (
                          <span className="text-[11px] font-mono text-amber-400">Unsaved changes</span>
                        )}
                        <Button
                          size="sm"
                          onClick={() => handleSaveEndpoint(key)}
                          disabled={editState.saving || !editState.isDirty || !!editState.jsonError}
                          className="h-7 text-xs gap-1.5 bg-primary text-primary-foreground font-semibold"
                        >
                          <IconDeviceFloppy className="size-3.5" />
                          {editState.saving ? "Saving…" : "Save Schema"}
                        </Button>
                      </div>
                    </div>

                    {/* Mode 1: Structured field table */}
                    {editState.mode === "fields" && (
                      <div className="space-y-2">
                        {editState.props.length === 0 ? (
                          <div className="text-center py-6 text-xs text-muted-foreground border border-dashed border-border rounded-xl">
                            No top-level object properties detected in this response payload.
                          </div>
                        ) : (
                          <div className="overflow-x-auto rounded-xl border border-border">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-muted/50 border-b border-border text-muted-foreground font-mono">
                                <tr>
                                  <th className="p-2.5">Field Name</th>
                                  <th className="p-2.5">Type</th>
                                  <th className="p-2.5 text-center">Required</th>
                                  <th className="p-2.5">Description</th>
                                  <th className="p-2.5 text-right">Actions</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border">
                                {editState.props.map((prop, pIdx) => (
                                  <tr key={pIdx} className="hover:bg-muted/30">
                                    <td className="p-2 font-mono">
                                      <Input
                                        value={prop.name}
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "name", e.target.value)
                                        }
                                        className="h-7 text-xs font-mono"
                                      />
                                    </td>
                                    <td className="p-2">
                                      <select
                                        value={prop.type}
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "type", e.target.value)
                                        }
                                        className="h-7 rounded-md border border-input bg-background px-2 text-xs font-mono text-foreground focus:outline-none"
                                      >
                                        <option value="string">string</option>
                                        <option value="integer">integer</option>
                                        <option value="number">number</option>
                                        <option value="boolean">boolean</option>
                                        <option value="array">array</option>
                                        <option value="object">object</option>
                                      </select>
                                    </td>
                                    <td className="p-2 text-center">
                                      <input
                                        type="checkbox"
                                        checked={prop.required}
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "required", e.target.checked)
                                        }
                                        className="size-4 accent-primary rounded cursor-pointer"
                                      />
                                    </td>
                                    <td className="p-2">
                                      <Input
                                        value={prop.description || ""}
                                        placeholder="Optional description"
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "description", e.target.value)
                                        }
                                        className="h-7 text-xs"
                                      />
                                    </td>
                                    <td className="p-2 text-right">
                                      <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleRemoveProperty(key, pIdx)}
                                        className="size-7 text-muted-foreground hover:text-destructive"
                                      >
                                        <IconTrash className="size-3.5" />
                                      </Button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleAddProperty(key)}
                          className="text-xs h-7 gap-1 font-mono"
                        >
                          <IconPlus className="size-3.5" />
                          Add Property
                        </Button>
                      </div>
                    )}

                    {/* Mode 2: Raw JSON Editor */}
                    {editState.mode === "json" && (
                      <div className="space-y-1.5">
                        <textarea
                          rows={8}
                          value={editState.rawJson}
                          onChange={(e) => handleRawJsonChange(key, e.target.value)}
                          className={`w-full rounded-xl border p-3 font-mono text-xs bg-background focus:outline-none leading-relaxed ${
                            editState.jsonError
                              ? "border-rose-500 focus:ring-1 focus:ring-rose-500"
                              : "border-border focus:ring-1 focus:ring-primary"
                          }`}
                        />
                        {editState.jsonError && (
                          <p className="text-xs text-rose-400 font-mono flex items-center gap-1">
                            <IconAlertTriangle className="size-3.5" />
                            Syntax error: {editState.jsonError}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Sticky Bottom Floating Action Bar ─────────────────────────────── */}
      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-border/60 bg-background/95 backdrop-blur-md p-4 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 text-xs font-mono text-muted-foreground">
            <span className="text-foreground font-semibold">
              {metrics.included} of {metrics.total} endpoints included
            </span>
            {metrics.excluded > 0 && <span className="text-amber-400">({metrics.excluded} excluded)</span>}
            {metrics.modified > 0 && (
              <Badge variant="outline" className="text-[10px] font-mono border-primary/40 text-primary">
                {metrics.modified} unsaved edits
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.back()}
              className="text-xs"
            >
              Cancel
            </Button>

            <Button
              size="sm"
              onClick={handleApprove}
              disabled={approving || metrics.included <= 0}
              className="gap-2 bg-primary text-primary-foreground font-semibold px-5 shadow-sm"
            >
              {approving ? (
                <>
                  <div className="size-3.5 rounded-full border-2 border-primary-foreground border-t-transparent animate-spin" />
                  Generating Specifications…
                </>
              ) : (
                <>
                  <IconCircleCheck className="size-4" />
                  Approve & Export Spec
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* ── Approval Success Modal ────────────────────────────────────────── */}
      <Dialog
        open={approveSuccessDialog.open}
        onOpenChange={(open) => {
          if (!open) {
            setApproveSuccessDialog((prev) => ({ ...prev, open: false }));
            router.push(`/reports/${crawlId}/drift`);
          }
        }}
      >
        <DialogContent className="max-w-md p-6 rounded-2xl bg-card border border-border shadow-2xl">
          <DialogHeader>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-2">
              <IconCircleCheck className="size-6" />
            </div>
            <DialogTitle className="text-lg font-bold text-foreground">
              Crawl Approved & Exported
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
              Your reviewed schema corrections and endpoint exclusions have been locked and
              synthesized into complete OpenAPI 3.0.3 and Postman specifications.
            </DialogDescription>
          </DialogHeader>

          <div className="rounded-xl border border-border/60 bg-muted/20 p-3 space-y-1.5 font-mono text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Exported Endpoints:</span>
              <span className="font-bold text-foreground">{approveSuccessDialog.capturedCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Excluded Endpoints:</span>
              <span className="text-muted-foreground">{approveSuccessDialog.excludedCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Status:</span>
              <span className="text-emerald-400 font-bold">completed</span>
            </div>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2 pt-2">
            <Link href={`/reports/${crawlId}/drift`} className="w-full sm:w-auto flex-1">
              <Button variant="outline" className="w-full gap-1.5 text-xs">
                <IconGitCompare className="size-3.5" />
                View Drift Diff
              </Button>
            </Link>
            <Link href="/chat" className="w-full sm:w-auto flex-1">
              <Button className="w-full gap-1.5 text-xs bg-primary text-primary-foreground font-semibold">
                <IconSparkles className="size-3.5" />
                Query in Chat
              </Button>
            </Link>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
