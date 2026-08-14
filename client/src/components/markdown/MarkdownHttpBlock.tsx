"use client";

import React, { useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { HttpBlockProps } from "./types";

const METHOD_STYLES: Record<
  HttpBlockProps["method"],
  { badge: string; border: string; bg: string; text: string }
> = {
  GET: {
    badge: "bg-blue-500/15 text-blue-500 dark:text-blue-400 border-blue-500/30",
    border: "border-blue-500/20",
    bg: "bg-blue-500/5",
    text: "text-blue-400",
  },
  POST: {
    badge: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    border: "border-emerald-500/20",
    bg: "bg-emerald-500/5",
    text: "text-emerald-400",
  },
  PUT: {
    badge: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
    border: "border-amber-500/20",
    bg: "bg-amber-500/5",
    text: "text-amber-400",
  },
  PATCH: {
    badge: "bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30",
    border: "border-purple-500/20",
    bg: "bg-purple-500/5",
    text: "text-purple-400",
  },
  DELETE: {
    badge: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30",
    border: "border-rose-500/20",
    bg: "bg-rose-500/5",
    text: "text-rose-400",
  },
  OPTIONS: {
    badge: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-500/30",
    border: "border-cyan-500/20",
    bg: "bg-cyan-500/5",
    text: "text-cyan-400",
  },
  HEAD: {
    badge: "bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/30",
    border: "border-slate-500/20",
    bg: "bg-slate-500/5",
    text: "text-slate-400",
  },
};

export const MarkdownHttpBlock = ({
  method,
  url,
  headers,
  body,
  rawCode,
}: HttpBlockProps) => {
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedFull, setCopiedFull] = useState(false);

  const style = METHOD_STYLES[method] || METHOD_STYLES.GET;

  const handleCopyUrl = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(url);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 2000);
  };

  const handleCopyFull = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(rawCode);
    setCopiedFull(true);
    setTimeout(() => setCopiedFull(false), 2000);
  };

  return (
    <div
      className={cn(
        "my-3.5 rounded-xl overflow-hidden border shadow-xs transition-all",
        "bg-[#111318] dark:bg-[#131720] border-border/70 text-slate-100",
        style.border
      )}
    >
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5 bg-[#181c26] dark:bg-[#181d28] border-b border-border/40 select-none">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <span
            className={cn(
              "px-2 py-0.5 rounded-md font-mono text-[11px] font-bold tracking-wider uppercase border shrink-0",
              style.badge
            )}
          >
            {method}
          </span>
          <span
            className="font-mono text-xs text-slate-200 truncate select-all"
            title={url}
          >
            {url}
          </span>
        </div>

        {/* Copy actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={handleCopyUrl}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-slate-200 transition-colors px-2 py-1 rounded-md hover:bg-slate-800/80 cursor-pointer"
            title="Copy URL only"
          >
            {copiedUrl ? (
              <>
                <CheckIcon className="size-3 text-emerald-400" />
                <span className="text-emerald-400 font-medium">URL Copied</span>
              </>
            ) : (
              <>
                <CopyIcon className="size-3" />
                <span>Copy URL</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleCopyFull}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-slate-200 transition-colors px-2 py-1 rounded-md hover:bg-slate-800/80 cursor-pointer"
            title="Copy full HTTP request"
          >
            {copiedFull ? (
              <>
                <CheckIcon className="size-3 text-emerald-400" />
                <span className="text-emerald-400 font-medium">Copied</span>
              </>
            ) : (
              <>
                <CopyIcon className="size-3" />
                <span>Copy All</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Optional Headers and Body sections */}
      {(headers || body) && (
        <div className="p-3 space-y-2 text-xs font-mono">
          {headers && (
            <div className="space-y-1 pb-2 border-b border-slate-800/60">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Headers
              </span>
              <div className="space-y-0.5 text-slate-300">
                {Object.entries(headers).map(([key, val]) => (
                  <div key={key} className="flex gap-2">
                    <span className="text-primary/90 font-medium">{key}:</span>
                    <span className="text-slate-300 break-all">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {body && (
            <div className="space-y-1">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Request Body
              </span>
              <div className="overflow-x-auto p-2.5 rounded-lg bg-black/40 border border-slate-800/50">
                <pre className="text-slate-200 whitespace-pre leading-relaxed m-0 text-xs">
                  {body}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
