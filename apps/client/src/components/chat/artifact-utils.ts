/**
 * artifact-utils.ts
 *
 * Scans raw markdown content from an AI response and extracts the
 * "primary artifact" — a diagram, code block, document, or table
 * that is best viewed in the Artifact Side Panel.
 */

import type { Artifact, ArtifactType } from "./ArtifactContext";

// Minimum lines a code block must have to be promoted to an artifact
const CODE_ARTIFACT_MIN_LINES = 14;

// ─── Helpers ───────────────────────────────────────────────────────────────────

let _idCounter = 0;
function nextId(): string {
  return `artifact-${Date.now()}-${++_idCounter}`;
}

/** Map common mermaid graph keywords to a friendly title */
function mermaidTitle(source: string): string {
  const s = source.trim().toLowerCase();
  if (s.startsWith("flowchart") || s.startsWith("graph")) return "Flow Diagram";
  if (s.startsWith("sequencediagram")) return "Sequence Diagram";
  if (s.startsWith("classDiagram") || s.startsWith("classdiagram")) return "Class Diagram";
  if (s.startsWith("erdiagram")) return "ER Diagram";
  if (s.startsWith("gantt")) return "Gantt Chart";
  if (s.startsWith("pie")) return "Pie Chart";
  if (s.startsWith("mindmap")) return "Mind Map";
  if (s.startsWith("statediagram")) return "State Diagram";
  if (s.startsWith("c4context") || s.startsWith("c4container")) return "C4 Architecture";
  return "Diagram";
}

/** Friendly display label for a code language */
function codeTitle(lang: string): string {
  const map: Record<string, string> = {
    typescript: "TypeScript",
    javascript: "JavaScript",
    tsx: "TSX",
    jsx: "JSX",
    python: "Python",
    bash: "Shell Script",
    sh: "Shell Script",
    sql: "SQL",
    json: "JSON",
    yaml: "YAML",
    yml: "YAML",
    go: "Go",
    rust: "Rust",
    java: "Java",
    php: "PHP",
    ruby: "Ruby",
    dockerfile: "Dockerfile",
    docker: "Dockerfile",
    nginx: "Nginx Config",
    html: "HTML",
    css: "CSS",
    scss: "SCSS",
    diff: "Diff",
    markdown: "Markdown",
    md: "Markdown",
  };
  return map[lang.toLowerCase()] ?? lang.toUpperCase();
}

// ─── Main extractor ────────────────────────────────────────────────────────────

/**
 * Extracts the most prominent artifact from a markdown string.
 * Priority order: mermaid → large code block → document heading → table.
 *
 * Returns null if no qualifying artifact is found.
 */
export function extractArtifact(markdown: string): Artifact | null {
  if (!markdown || markdown.trim().length < 20) return null;

  // ── 1. Mermaid diagrams (always promoted, any size) ─────────────────────────
  const mermaidRegex = /```mermaid\s*\n([\s\S]*?)```/i;
  const mermaidMatch = mermaidRegex.exec(markdown);
  if (mermaidMatch) {
    const source = mermaidMatch[1].trim();
    return {
      id: nextId(),
      type: "diagram",
      title: mermaidTitle(source),
      content: source,
    };
  }

  // ── 2. Large code blocks (>= CODE_ARTIFACT_MIN_LINES) ───────────────────────
  const codeRegex = /```(\w+)?\s*\n([\s\S]*?)```/g;
  let codeMatch: RegExpExecArray | null;
  while ((codeMatch = codeRegex.exec(markdown)) !== null) {
    const lang = (codeMatch[1] || "").toLowerCase();
    const body = codeMatch[2] || "";
    const lineCount = body.split("\n").length;
    // Skip http blocks — they have their own inline renderer
    if (lang === "http" || lang === "mermaid") continue;
    if (lineCount >= CODE_ARTIFACT_MIN_LINES) {
      return {
        id: nextId(),
        type: "code",
        title: `${codeTitle(lang)} · ${lineCount} lines`,
        content: body.trimEnd(),
        language: lang || "text",
      };
    }
  }

  // ── 3. Markdown tables (standalone, >= 3 rows) ───────────────────────────────
  const tableRegex = /(\|.+\|[\r\n]+\|[-| :]+\|[\r\n]+(?:\|.+\|[\r\n]*){2,})/;
  const tableMatch = tableRegex.exec(markdown);
  if (tableMatch) {
    const rows = tableMatch[1].split("\n").filter((l) => l.trim().startsWith("|")).length;
    if (rows >= 4) {
      return {
        id: nextId(),
        type: "table",
        title: `Table · ${rows - 2} rows`,
        content: tableMatch[1].trim(),
      };
    }
  }

  // ── 4. Document-style response (starts with # heading, long) ────────────────
  const isDoc =
    markdown.trimStart().startsWith("#") &&
    markdown.length > 600 &&
    (markdown.match(/^#{1,3} /gm) || []).length >= 2;
  if (isDoc) {
    const firstHeading = (markdown.match(/^#+ (.+)/m) || [])[1] || "Document";
    return {
      id: nextId(),
      type: "document",
      title: firstHeading.trim(),
      content: markdown.trim(),
    };
  }

  return null;
}

/** Badge label shown in the panel header */
export function artifactBadgeLabel(type: ArtifactType, language?: string): string {
  if (type === "diagram") return "Diagram";
  if (type === "table") return "Table";
  if (type === "document") return "MD";
  if (type === "code") return (language || "code").toUpperCase().slice(0, 4);
  return "File";
}
