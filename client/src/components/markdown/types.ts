import type { ReactNode } from "react";

export interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
  className?: string;
  enableMermaid?: boolean;
  enableMath?: boolean;
  enableHtml?: boolean;
}

export interface CodeBlockProps {
  language?: string;
  code: string;
  inline?: boolean;
  className?: string;
}

export interface HttpBlockProps {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "OPTIONS" | "HEAD";
  url: string;
  headers?: Record<string, string>;
  body?: string;
  rawCode: string;
}

export interface CalloutProps {
  type: "note" | "tip" | "important" | "warning" | "caution";
  title?: string;
  children: ReactNode;
  className?: string;
}

export interface MermaidProps {
  chart: string;
  className?: string;
}

export interface MathBlockProps {
  math: string;
  inline?: boolean;
  className?: string;
}
