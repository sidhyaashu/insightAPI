"use client";

import React, { useMemo, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import type { PluggableList } from "unified";
import { cn } from "@/lib/utils";
import type { MarkdownRendererProps } from "./types";
import { repairStreamingMarkdown } from "./markdown-utils";

import {
  MarkdownH1,
  MarkdownH2,
  MarkdownH3,
  MarkdownH4,
  MarkdownH5,
  MarkdownH6,
} from "./MarkdownHeading";
import { MarkdownParagraph } from "./MarkdownParagraph";
import { MarkdownLink } from "./MarkdownLink";
import { MarkdownUl, MarkdownOl, MarkdownLi, MarkdownCheckbox } from "./MarkdownList";
import { MarkdownBlockquote } from "./MarkdownBlockquote";
import {
  MarkdownTable,
  MarkdownTableHead,
  MarkdownTableBody,
  MarkdownTableRow,
  MarkdownTableHeaderCell,
  MarkdownTableCell,
} from "./MarkdownTable";
import { MarkdownHorizontalRule } from "./MarkdownHorizontalRule";
import { MarkdownImage } from "./MarkdownImage";
import { CodeBlock, InlineCode } from "./MarkdownCode";
import { MarkdownMermaid } from "./MarkdownMermaid";

// Sanitization schema extending default with KaTeX math tags & classNames
const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    "*": [
      ...(defaultSchema.attributes?.["*"] || []),
      "className",
      "style",
      "align",
    ],
    code: [
      ...(defaultSchema.attributes?.code || []),
      "className",
    ],
    span: [
      ...(defaultSchema.attributes?.span || []),
      "className",
      "aria-hidden",
    ],
    div: [
      ...(defaultSchema.attributes?.div || []),
      "className",
    ],
    a: [
      ...(defaultSchema.attributes?.a || []),
      "target",
      "rel",
      "href",
    ],
    svg: [
      ...(defaultSchema.attributes?.svg || []),
      "className",
      "viewBox",
      "preserveAspectRatio",
      "width",
      "height",
      "fill",
      "stroke",
      "xmlns",
      "aria-hidden",
    ],
    path: [
      ...(defaultSchema.attributes?.path || []),
      "d",
      "fill",
      "stroke",
      "strokeWidth",
    ],
    line: [
      ...(defaultSchema.attributes?.line || []),
      "x1",
      "y1",
      "x2",
      "y2",
      "stroke",
      "strokeWidth",
    ],
  },
  tagNames: [
    ...(defaultSchema.tagNames || []),
    "math",
    "semantics",
    "mrow",
    "mi",
    "mo",
    "mn",
    "ms",
    "mspace",
    "mtext",
    "msup",
    "msub",
    "msubsup",
    "mfrac",
    "mroot",
    "msqrt",
    "mtable",
    "mtr",
    "mtd",
    "annotation",
    "svg",
    "path",
    "line",
    "g",
  ],
};

class MarkdownErrorBoundary extends React.Component<
  { children: React.ReactNode; fallbackContent: string },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode; fallbackContent: string }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.warn("MarkdownRenderer error caught by boundary:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="whitespace-pre-wrap font-sans text-xs sm:text-sm text-foreground/90 leading-relaxed">
          {this.props.fallbackContent}
        </div>
      );
    }
    return this.props.children;
  }
}

export const MarkdownRenderer = memo(
  ({
    content,
    isStreaming = false,
    className,
    enableMath = true,
    enableHtml = false,
    /**
     * When true, mermaid code fences that have been promoted to the
     * ArtifactPanel are rendered as a compact ArtifactCard tile instead of
     * the full inline SVG canvas. Prevents the Claude.ai anti-pattern of
     * showing the same diagram in both the chat thread and the right panel.
     */
    suppressInlineArtifacts = false,
  }: MarkdownRendererProps & { suppressInlineArtifacts?: boolean }) => {
    // 1. Repair streaming markdown tokens (unclosed fences, math blocks)
    const processedContent = useMemo(
      () => repairStreamingMarkdown(content, isStreaming),
      [content, isStreaming]
    );

    // 2. Configure remark & rehype plugins
    const remarkPlugins = useMemo<PluggableList>(() => {
      const plugins: PluggableList = [remarkGfm];
      if (enableMath) {
        plugins.push(remarkMath as any);
      }
      return plugins;
    }, [enableMath]);

    const rehypePlugins = useMemo<PluggableList>(() => {
      const plugins: PluggableList = [];
      if (enableHtml) {
        plugins.push(rehypeRaw as any);
      }
      if (enableMath) {
        plugins.push(rehypeKatex as any);
      }
      plugins.push([rehypeSanitize as any, sanitizeSchema]);
      return plugins;
    }, [enableMath, enableHtml]);

    // 3. Define custom component handlers
    const components = useMemo(() => {
      return {
        h1: MarkdownH1,
        h2: MarkdownH2,
        h3: MarkdownH3,
        h4: MarkdownH4,
        h5: MarkdownH5,
        h6: MarkdownH6,
        p: MarkdownParagraph,
        a: MarkdownLink,
        ul: MarkdownUl,
        ol: MarkdownOl,
        li: MarkdownLi,
        blockquote: MarkdownBlockquote,
        table: MarkdownTable,
        thead: MarkdownTableHead,
        tbody: MarkdownTableBody,
        tr: MarkdownTableRow,
        th: MarkdownTableHeaderCell,
        td: MarkdownTableCell,
        hr: MarkdownHorizontalRule,
        img: MarkdownImage,
        input: ({ type, checked }: { type?: string; checked?: boolean }) => {
          if (type === "checkbox") {
            return <MarkdownCheckbox checked={checked} />;
          }
          return <input type={type} checked={checked} readOnly />;
        },
        code: ({
          node,
          inline,
          className,
          children,
        }: {
          node?: { position?: { start: { line: number }; end: { line: number } } };
          inline?: boolean;
          className?: string;
          children?: React.ReactNode;
        }) => {
          const match = /language-(\w+)/.exec(className || "");
          const language = match ? match[1] : "";
          const rawCode = String(children).replace(/\n$/, "");

          // Check if inline code or block code
          const isInline =
            inline ||
            (!match &&
              !rawCode.includes("\n") &&
              node?.position?.start.line === node?.position?.end.line);

          if (isInline) {
            return <InlineCode className={className}>{children}</InlineCode>;
          }

          // Mermaid — delegate to MarkdownMermaid which handles suppression
          if (language === "mermaid") {
            return (
              <MarkdownMermaid
                chart={rawCode}
                suppressPanel={suppressInlineArtifacts}
              />
            );
          }

          return <CodeBlock language={language} code={rawCode} className={className} />;
        },
      };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [suppressInlineArtifacts]);

    if (!content) return null;

    return (
      <MarkdownErrorBoundary fallbackContent={content}>
        <div
          className={cn(
            "w-full text-foreground/95 text-xs sm:text-sm leading-relaxed overflow-hidden break-words font-sans",
            className
          )}
        >
          <ReactMarkdown
            remarkPlugins={remarkPlugins}
            rehypePlugins={rehypePlugins}
            components={components}
          >
            {processedContent}
          </ReactMarkdown>

          {isStreaming && (
            <span
              className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle rounded-xs"
              aria-label="Generating response..."
            />
          )}
        </div>
      </MarkdownErrorBoundary>
    );
  }
);

MarkdownRenderer.displayName = "MarkdownRenderer";
export default MarkdownRenderer;
