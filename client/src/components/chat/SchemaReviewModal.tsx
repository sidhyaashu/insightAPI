"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
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
  IconPlus,
  IconTrash,
  IconSearch,
  IconLoader2,
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
import { cn } from "@/lib/utils";

// ── Method badge styles ───────────────────────────────────────────────────────
const METHOD_COLORS: Record<string, string> = {
  GET: "bg-blue-500/10 text-blue-400 border-blue-500/25",
  POST: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
  PUT: "bg-amber-500/10 text-amber-400 border-amber-500/25",
  PATCH: "bg-purple-500/10 text-purple-400 border-purple-500/25",
  DELETE: "bg-rose-500/10 text-rose-400 border-rose-500/25",
};

// ── Confidence rating helpers ─────────────────────────────────────────────────
function getConfidenceStyle(confidence: number) {
  if (confidence < 0.5) {
    return {
      label: "Low Confidence",
      color: "bg-rose-500/10 text-rose-400 border-rose-500/25",
      indicator: "bg-rose-500",
    };
  }
  if (confidence < 0.75) {
    return {
      label: "Medium Confidence",
      color: "bg-amber-500/10 text-amber-400 border-amber-500/25",
      indicator: "bg-amber-500",
    };
  }
  return {
    label: "High Confidence",
    color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
    indicator: "bg-emerald-500",
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

export interface SchemaReviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sessionId: string;
  targetUrl: string;
  onApproveSuccess?: (session: CrawlSession) => void;
}

export function SchemaReviewModal({
  open,
  onOpenChange,
  sessionId,
  targetUrl,
  onApproveSuccess,
}: SchemaReviewModalProps) {
  const [endpoints, setEndpoints] = useState<EndpointReviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [approving, setApproving] = useState(false);

  // Edit states per endpoint
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

  // ── Load endpoint review data ───────────────────────────────────────────────
  const loadData = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await reviewApi.listEndpoints(sessionId);
      setEndpoints(data);

      const initialEdits: typeof editStates = {};
      data.forEach((ep) => {
        const schema = ep.reviewed_schema || ep.schema_json || {};
        initialEdits[ep.endpoint_key] = {
          rawJson: JSON.stringify(schema, null, 2),
          jsonError: null,
          props: extractPropertiesFromSchema(schema),
          isExcluded: ep.is_excluded ?? false,
          mode: "fields",
          isDirty: false,
          saving: false,
        };
      });
      setEditStates(initialEdits);

      // Default expand the first endpoint if available
      if (data.length > 0) {
        setExpandedKeys(new Set([data[0].endpoint_key]));
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to load crawl endpoints for review.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (open && sessionId) {
      loadData();
    }
  }, [open, sessionId, loadData]);

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
      await reviewApi.patchEndpoint(sessionId, key, { is_excluded: newExcluded });
      toast.success(newExcluded ? `Excluded '${key}' from export` : `Included '${key}' in export`);
    } catch {
      toast.error("Failed to update exclusion status");
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
      const updated = await reviewApi.patchEndpoint(sessionId, key, {
        schema: parsedSchema,
        is_excluded: state.isExcluded,
      });

      setEndpoints((prev) =>
        prev.map((e) => (e.endpoint_key === key ? { ...e, ...updated, has_review: true } : e))
      );

      setEditStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], isDirty: false, saving: false },
      }));

      toast.success(`Schema updated for ${key}`);
    } catch {
      toast.error(`Failed to save schema for ${key}`);
      setEditStates((prev) => ({
        ...prev,
        [key]: { ...prev[key], saving: false },
      }));
    }
  };

  // ── Approve & Export Spec ───────────────────────────────────────────────────
  const handleApprove = async () => {
    if (metrics.included <= 0) {
      toast.error("At least one endpoint must be included in export.");
      return;
    }

    setApproving(true);
    try {
      // 1. Save any pending dirty edits
      const dirtyKeys = Object.entries(editStates)
        .filter(([, s]) => s.isDirty)
        .map(([k]) => k);

      for (const key of dirtyKeys) {
        const state = editStates[key];
        if (!state.jsonError) {
          try {
            const parsed = JSON.parse(state.rawJson);
            await reviewApi.patchEndpoint(sessionId, key, {
              schema: parsed,
              is_excluded: state.isExcluded,
            });
          } catch {}
        }
      }

      // 2. Call approve endpoint
      await reviewApi.approveCrawl(sessionId);

      // 3. Fetch completed session with generated specs and report
      let updatedSession = await crawlsApi.getCrawlById(sessionId);
      try {
        const report = await crawlsApi.getReport(sessionId);
        if (report) {
          updatedSession = {
            ...updatedSession,
            openapi_spec: report.openapi_spec || updatedSession.openapi_spec,
            postman_collection: report.postman_collection || updatedSession.postman_collection,
            markdown_docs: report.markdown_docs || updatedSession.markdown_docs,
          };
        }
      } catch {}

      toast.success("Crawl approved! OpenAPI & Postman specifications synthesized.");
      onOpenChange(false);
      onApproveSuccess?.(updatedSession);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to approve crawl.";
      toast.error(msg);
    } finally {
      setApproving(false);
    }
  };

  // ── Filtered endpoints ──────────────────────────────────────────────────────
  const filteredEndpoints = useMemo(() => {
    if (!searchQuery.trim()) return endpoints;
    const q = searchQuery.toLowerCase();
    return endpoints.filter(
      (e) =>
        e.endpoint_key.toLowerCase().includes(q) ||
        e.method.toLowerCase().includes(q) ||
        (e.path && e.path.toLowerCase().includes(q))
    );
  }, [endpoints, searchQuery]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[88vh] flex flex-col p-0 bg-card border border-border/80 shadow-2xl rounded-2xl overflow-hidden">
        {/* Header */}
        <DialogHeader className="p-5 border-b border-border/60 bg-muted/20 shrink-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/25 shrink-0">
                  <IconSparkles className="size-4" />
                </div>
                <DialogTitle className="text-base font-bold text-foreground">
                  Schema Review & Endpoint Curation
                </DialogTitle>
              </div>
              <DialogDescription className="text-xs text-muted-foreground font-mono truncate max-w-lg">
                Target: {targetUrl} &bull; Session: {sessionId}
              </DialogDescription>
            </div>

            {/* Metrics Chips */}
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <div className="px-2.5 py-1 rounded-lg bg-muted/40 border border-border/60 font-mono text-[11px] text-muted-foreground">
                Total: <strong className="text-foreground">{metrics.total}</strong>
              </div>
              <div className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/25 font-mono text-[11px] text-emerald-400">
                Included: <strong>{metrics.included}</strong>
              </div>
              {metrics.excluded > 0 && (
                <div className="px-2.5 py-1 rounded-lg bg-rose-500/10 border border-rose-500/25 font-mono text-[11px] text-rose-400">
                  Excluded: <strong>{metrics.excluded}</strong>
                </div>
              )}
            </div>
          </div>
        </DialogHeader>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-[300px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
              <IconLoader2 className="size-6 animate-spin text-primary" />
              <span className="text-xs font-mono">Loading captured endpoints for review…</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
              <div className="p-3 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive">
                <IconAlertTriangle className="size-5" />
              </div>
              <p className="text-xs text-muted-foreground max-w-sm">{error}</p>
              <Button variant="outline" size="sm" onClick={loadData} className="gap-1.5 text-xs">
                <IconRefresh className="size-3.5" /> Retry
              </Button>
            </div>
          ) : endpoints.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-xs font-mono">
              No endpoint snapshots found for this crawl.
            </div>
          ) : (
            <>
              {/* Search filter bar */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <IconSearch className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Filter endpoints by path or method..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="h-8 text-xs pl-8 font-mono bg-muted/20"
                  />
                </div>
              </div>

              {/* Endpoints list */}
              <div className="space-y-2.5">
                {filteredEndpoints.map((ep) => {
                  const key = ep.endpoint_key;
                  const state = editStates[key] || {
                    rawJson: "{}",
                    jsonError: null,
                    props: [],
                    isExcluded: false,
                    mode: "fields",
                    isDirty: false,
                    saving: false,
                  };
                  const isExpanded = expandedKeys.has(key);
                  const conf = getConfidenceStyle(ep.confidence);

                  return (
                    <div
                      key={key}
                      className={cn(
                        "rounded-xl border transition-all overflow-hidden",
                        state.isExcluded
                          ? "border-border/30 bg-muted/10 opacity-60"
                          : isExpanded
                          ? "border-primary/40 bg-card shadow-md"
                          : "border-border/60 bg-card/60 hover:bg-card hover:border-border"
                      )}
                    >
                      {/* Endpoint Row Summary */}
                      <div
                        onClick={() => toggleExpand(key)}
                        className="flex items-center justify-between gap-3 p-3 cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2.5 min-w-0 flex-1">
                          <Badge
                            variant="outline"
                            className={cn(
                              "font-mono font-bold text-[10px] px-1.5 py-0 h-5 shrink-0 uppercase",
                              METHOD_COLORS[ep.method] || "bg-muted text-foreground"
                            )}
                          >
                            {ep.method}
                          </Badge>
                          <span
                            className={cn(
                              "font-mono text-xs truncate",
                              state.isExcluded ? "line-through text-muted-foreground" : "text-foreground font-medium"
                            )}
                          >
                            {ep.path || ep.endpoint_key}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                            HTTP {ep.status_code}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {/* Confidence Badge */}
                          <Badge
                            variant="outline"
                            className={cn("text-[9px] font-mono px-1.5 py-0 h-4", conf.color)}
                          >
                            {(ep.confidence * 100).toFixed(0)}% conf
                          </Badge>

                          {/* Exclude / Include Button */}
                          <Button
                            size="sm"
                            variant={state.isExcluded ? "secondary" : "outline"}
                            onClick={(e) => handleToggleExclude(key, e)}
                            className={cn(
                              "h-6 text-[10px] px-2 gap-1 cursor-pointer",
                              state.isExcluded
                                ? "text-rose-400 hover:bg-rose-500/10"
                                : "text-muted-foreground hover:text-foreground"
                            )}
                          >
                            {state.isExcluded ? (
                              <>
                                <IconEyeOff className="size-3" /> Excluded
                              </>
                            ) : (
                              <>
                                <IconEye className="size-3" /> Included
                              </>
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* Expanded Schema Editor */}
                      {isExpanded && (
                        <div className="p-3.5 border-t border-border/50 bg-muted/10 space-y-3">
                          {/* Mode Toggle & Save row */}
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <Button
                                size="sm"
                                variant={state.mode === "fields" ? "secondary" : "ghost"}
                                onClick={() =>
                                  setEditStates((prev) => ({
                                    ...prev,
                                    [key]: { ...prev[key], mode: "fields" },
                                  }))
                                }
                                className="h-6 text-[10px] px-2 gap-1 cursor-pointer font-mono"
                              >
                                <IconListDetails className="size-3" /> Fields
                              </Button>
                              <Button
                                size="sm"
                                variant={state.mode === "json" ? "secondary" : "ghost"}
                                onClick={() =>
                                  setEditStates((prev) => ({
                                    ...prev,
                                    [key]: { ...prev[key], mode: "json" },
                                  }))
                                }
                                className="h-6 text-[10px] px-2 gap-1 cursor-pointer font-mono"
                              >
                                <IconCode className="size-3" /> JSON Schema
                              </Button>
                            </div>

                            <Button
                              size="sm"
                              onClick={() => handleSaveEndpoint(key)}
                              disabled={state.saving || !state.isDirty}
                              className="h-6 text-[10px] px-2.5 gap-1 bg-primary text-primary-foreground font-semibold cursor-pointer"
                            >
                              <IconDeviceFloppy className="size-3" />
                              {state.saving ? "Saving..." : state.isDirty ? "Save Changes" : "Saved"}
                            </Button>
                          </div>

                          {/* Fields View */}
                          {state.mode === "fields" ? (
                            <div className="space-y-2">
                              {state.props.length === 0 ? (
                                <div className="text-[11px] font-mono text-muted-foreground p-3 rounded-lg bg-muted/20 text-center">
                                  No properties defined in schema.
                                </div>
                              ) : (
                                <div className="space-y-1.5 font-mono text-xs">
                                  <div className="grid grid-cols-12 gap-2 text-[10px] font-semibold text-muted-foreground uppercase px-1">
                                    <span className="col-span-4">Field Name</span>
                                    <span className="col-span-3">Type</span>
                                    <span className="col-span-2 text-center">Req</span>
                                    <span className="col-span-3 text-right">Action</span>
                                  </div>
                                  {state.props.map((prop, pIdx) => (
                                    <div
                                      key={pIdx}
                                      className="grid grid-cols-12 gap-2 items-center p-1.5 rounded-lg bg-card border border-border/40"
                                    >
                                      <input
                                        className="col-span-4 bg-transparent text-foreground text-xs px-1.5 py-0.5 focus:outline-hidden border-b border-transparent focus:border-primary"
                                        value={prop.name}
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "name", e.target.value)
                                        }
                                        placeholder="field_name"
                                      />
                                      <select
                                        className="col-span-3 bg-muted/40 text-foreground text-[11px] rounded-md px-1.5 py-0.5 border border-border/50 focus:outline-hidden"
                                        value={prop.type}
                                        onChange={(e) =>
                                          handlePropertyChange(key, pIdx, "type", e.target.value)
                                        }
                                      >
                                        <option value="string">string</option>
                                        <option value="number">number</option>
                                        <option value="integer">integer</option>
                                        <option value="boolean">boolean</option>
                                        <option value="object">object</option>
                                        <option value="array">array</option>
                                      </select>
                                      <div className="col-span-2 flex justify-center">
                                        <input
                                          type="checkbox"
                                          checked={prop.required}
                                          onChange={(e) =>
                                            handlePropertyChange(key, pIdx, "required", e.target.checked)
                                          }
                                          className="size-3.5 accent-primary rounded-xs"
                                        />
                                      </div>
                                      <div className="col-span-3 flex justify-end">
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => handleRemoveProperty(key, pIdx)}
                                          className="h-5 w-5 p-0 text-muted-foreground hover:text-destructive"
                                        >
                                          <IconTrash className="size-3" />
                                        </Button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleAddProperty(key)}
                                className="h-6 text-[10px] px-2 gap-1 border-dashed font-mono"
                              >
                                <IconPlus className="size-3" /> Add Property
                              </Button>
                            </div>
                          ) : (
                            /* JSON Schema Raw Editor */
                            <div className="space-y-1.5 font-mono">
                              <textarea
                                value={state.rawJson}
                                onChange={(e) => handleRawJsonChange(key, e.target.value)}
                                rows={8}
                                className="w-full text-xs font-mono bg-muted/30 p-2.5 rounded-lg border border-border/60 focus:outline-hidden focus:border-primary text-foreground resize-y"
                              />
                              {state.jsonError && (
                                <p className="text-[10px] text-rose-400">{state.jsonError}</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="p-4 border-t border-border/60 bg-muted/20 shrink-0 flex items-center justify-between gap-3">
          <div className="text-xs text-muted-foreground font-mono">
            {metrics.included} of {metrics.total} endpoints ready for export
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs h-8 px-3 cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleApprove}
              disabled={approving || metrics.included <= 0}
              className="text-xs h-8 px-4 gap-1.5 bg-primary text-primary-foreground font-semibold cursor-pointer shadow-xs"
            >
              {approving ? (
                <>
                  <IconLoader2 className="size-3.5 animate-spin" />
                  Synthesizing Specs...
                </>
              ) : (
                <>
                  <IconCircleCheck className="size-3.5" />
                  Approve & Synthesize Specs
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
