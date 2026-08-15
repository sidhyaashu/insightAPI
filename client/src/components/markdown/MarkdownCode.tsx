"use client";

import React, { useState, useMemo, memo } from "react";
import Prism from "prismjs";
import "prismjs/components/prism-typescript";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-jsx";
import "prismjs/components/prism-tsx";
import "prismjs/components/prism-python";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-shell-session";
import "prismjs/components/prism-sql";
import "prismjs/components/prism-json";
import "prismjs/components/prism-yaml";
import "prismjs/components/prism-c";
import "prismjs/components/prism-cpp";
import "prismjs/components/prism-go";
import "prismjs/components/prism-rust";
import "prismjs/components/prism-java";
import "prismjs/components/prism-php";
import "prismjs/components/prism-ruby";
import "prismjs/components/prism-docker";
import "prismjs/components/prism-nginx";
import "prismjs/components/prism-http";
import "prismjs/components/prism-diff";
import "prismjs/components/prism-markdown";
import "prismjs/components/prism-scss";

import {
  CheckIcon,
  CopyIcon,
  FileCodeIcon,
  TerminalIcon,
  DatabaseIcon,
  BracesIcon,
  WrapTextIcon,
  PanelRightOpenIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CodeBlockProps } from "./types";
import { parseHttpSnippet } from "./markdown-utils";
import { MarkdownHttpBlock } from "./MarkdownHttpBlock";
import { MarkdownMermaid } from "./MarkdownMermaid";
import { useArtifact } from "@/components/chat/ArtifactContext";

// Map aliases to Prism registered language identifiers
const LANGUAGE_MAP: Record<string, string> = {
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
  py: "python",
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  bash: "bash",
  yml: "yaml",
  yaml: "yaml",
  json: "json",
  sql: "sql",
  c: "c",
  cpp: "cpp",
  "c++": "cpp",
  golang: "go",
  go: "go",
  rs: "rust",
  rust: "rust",
  java: "java",
  php: "php",
  rb: "ruby",
  ruby: "ruby",
  docker: "docker",
  dockerfile: "docker",
  nginx: "nginx",
  http: "http",
  diff: "diff",
  md: "markdown",
  markdown: "markdown",
  html: "markup",
  xml: "markup",
  css: "css",
  scss: "scss",
};

const getLanguageIcon = (lang: string) => {
  const l = lang.toLowerCase();
  if (["bash", "sh", "shell", "zsh", "terminal"].includes(l)) {
    return <TerminalIcon className="size-3.5 text-emerald-400" />;
  }
  if (["sql", "database"].includes(l)) {
    return <DatabaseIcon className="size-3.5 text-blue-400" />;
  }
  if (["json", "yaml", "yml", "xml"].includes(l)) {
    return <BracesIcon className="size-3.5 text-amber-400" />;
  }
  return <FileCodeIcon className="size-3.5 text-primary" />;
};

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export const InlineCode = memo(({ children, className }: { children: React.ReactNode; className?: string }) => {
  return (
    <code
      className={cn(
        "font-mono text-[0.875em] bg-muted/80 text-foreground border border-border/50 px-1.5 py-0.5 rounded-md mx-0.5 break-words font-medium",
        className
      )}
    >
      {children}
    </code>
  );
});

InlineCode.displayName = "InlineCode";

export const CodeBlock = memo(({ language = "", code, className }: CodeBlockProps) => {
  const [copied, setCopied] = useState(false);
  const [wrapLines, setWrapLines] = useState(false);
  const { openPanel } = useArtifact();

  const cleanLang = (language || "").toLowerCase().trim();
  const lineCount = code.split("\n").length;
  const isLargeBlock = lineCount >= 14;

  // Check if this is an HTTP API snippet
  const httpSnippet = parseHttpSnippet(code, cleanLang);
  if (httpSnippet) {
    return <MarkdownHttpBlock {...httpSnippet} />;
  }

  const prismLang = LANGUAGE_MAP[cleanLang] || cleanLang;
  const displayLang = cleanLang || "text";

  const highlightedHtml = useMemo(() => {
    try {
      if (prismLang && Prism.languages[prismLang]) {
        return Prism.highlight(code, Prism.languages[prismLang], prismLang);
      }
      return escapeHtml(code);
    } catch {
      return escapeHtml(code);
    }
  }, [code, prismLang]);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "group/code my-3.5 rounded-xl overflow-hidden border border-border/70 bg-[#121316] dark:bg-[#14161b] text-slate-100 shadow-xs font-mono text-xs max-w-full transition-all",
        className
      )}
    >
      {/* Code block header */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#191b20] dark:bg-[#1a1d24] border-b border-border/40 text-[11px] text-muted-foreground select-none">
        <div className="flex items-center gap-2">
          {getLanguageIcon(displayLang)}
          <span className="font-semibold uppercase tracking-wider text-slate-300 font-sans">
            {displayLang}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Wrap lines toggle */}
          <button
            type="button"
            onClick={() => setWrapLines(!wrapLines)}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded transition-colors cursor-pointer text-[11px]",
              wrapLines
                ? "bg-slate-800 text-primary font-medium"
                : "text-muted-foreground hover:text-slate-200 hover:bg-slate-800/60"
            )}
            title={wrapLines ? "Disable line wrap" : "Enable line wrap"}
          >
            <WrapTextIcon className="size-3" />
            <span className="hidden sm:inline font-sans text-[10px]">Wrap</span>
          </button>

          {/* Open in panel — only for large blocks */}
          {isLargeBlock && (
            <button
              type="button"
              onClick={() =>
                openPanel({
                  id: `code-${Date.now()}`,
                  type: "code",
                  title: `${displayLang.toUpperCase()} · ${lineCount} lines`,
                  content: code,
                  language: cleanLang,
                })
              }
              className="flex items-center gap-1 px-2 py-0.5 rounded text-muted-foreground hover:text-primary transition-colors cursor-pointer hover:bg-slate-800 text-[11px]"
              title="Open in side panel"
            >
              <PanelRightOpenIcon className="size-3" />
              <span className="font-sans hidden sm:inline">Panel</span>
            </button>
          )}

          {/* Copy button */}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-muted-foreground hover:text-white transition-colors cursor-pointer hover:bg-slate-800"
            title="Copy code"
          >
            {copied ? (
              <>
                <CheckIcon className="size-3 text-emerald-400" />
                <span className="text-emerald-400 font-sans font-medium">Copied!</span>
              </>
            ) : (
              <>
                <CopyIcon className="size-3" />
                <span className="font-sans">Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code content */}
      <div className="p-3.5 overflow-x-auto leading-relaxed">
        <pre
          className={cn(
            "m-0 font-mono text-[12.5px] tab-4",
            wrapLines ? "whitespace-pre-wrap break-words" : "whitespace-pre"
          )}
        >
          <code
            dangerouslySetInnerHTML={{ __html: highlightedHtml }}
            className={`language-${prismLang}`}
          />
        </pre>
      </div>
    </div>
  );
});

CodeBlock.displayName = "CodeBlock";
