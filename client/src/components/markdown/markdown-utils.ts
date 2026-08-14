import type { HttpBlockProps } from "./types";

/**
 * Repairs partially streamed markdown so that parsers don't break or jump
 * on unfinished code fences, math blocks, or inline formatting.
 */
export function repairStreamingMarkdown(content: string, isStreaming?: boolean): string {
  if (!isStreaming || !content) {
    return content || "";
  }

  let text = content;

  // 1. Repair unclosed code fences: ```lang ...
  const fenceMatches = text.match(/```/g);
  if (fenceMatches && fenceMatches.length % 2 !== 0) {
    text += "\n```";
  }

  // 2. Repair unclosed block math: $$ ...
  const blockMathMatches = text.match(/\$\$/g);
  if (blockMathMatches && blockMathMatches.length % 2 !== 0) {
    text += "\n$$";
  }

  // 3. Repair unclosed table rows if stream cut off in the middle of a line
  // If the last line contains a pipe `|` without a closing pipe or newline, we keep it as-is or let GFM handle it.

  return text;
}

/**
 * Validates URLs to prevent XSS (e.g. javascript:, vbscript:, data:).
 */
export function isSafeUrl(url?: string): boolean {
  if (!url) return false;
  const trimmed = url.trim().toLowerCase();

  // Allow relative URLs, anchors, mailto, tel
  if (
    trimmed.startsWith("/") ||
    trimmed.startsWith("#") ||
    trimmed.startsWith("mailto:") ||
    trimmed.startsWith("tel:")
  ) {
    return true;
  }

  // Allow safe http and https protocols
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return true;
  }

  // Reject javascript:, data:, vbscript: and any other unknown protocol
  return false;
}

/**
 * Attempts to parse an HTTP request snippet from code block text.
 */
export function parseHttpSnippet(code: string, language?: string): HttpBlockProps | null {
  if (!code) return null;
  const trimmed = code.trim();

  // First line inspection
  const lines = trimmed.split("\n");
  const firstLine = lines[0]?.trim() || "";

  // Regex to match "METHOD /path" or "METHOD http(s)://..."
  const match = firstLine.match(/^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(https?:\/\/[^\s]+|\/[^\s]*)/i);

  const isHttpLang = language?.toLowerCase() === "http" || language?.toLowerCase() === "rest";

  if (!match) {
    if (isHttpLang) {
      // If language is declared as http, try lenient match
      const lenientMatch = firstLine.match(/^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b/i);
      if (lenientMatch) {
        const method = lenientMatch[1].toUpperCase() as HttpBlockProps["method"];
        const url = firstLine.slice(lenientMatch[0].length).trim() || "/";
        return parseHttpDetails(method, url, lines.slice(1), trimmed);
      }
    }
    return null;
  }

  const method = match[1].toUpperCase() as HttpBlockProps["method"];
  const url = match[2];
  return parseHttpDetails(method, url, lines.slice(1), trimmed);
}

function parseHttpDetails(
  method: HttpBlockProps["method"],
  url: string,
  remainingLines: string[],
  rawCode: string
): HttpBlockProps {
  const headers: Record<string, string> = {};
  let bodyStartIndex = -1;

  for (let i = 0; i < remainingLines.length; i++) {
    const line = remainingLines[i].trim();
    if (line === "") {
      // Empty line marks transition from headers to body
      bodyStartIndex = i + 1;
      break;
    }
    const headerMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (headerMatch) {
      headers[headerMatch[1]] = headerMatch[2];
    } else {
      // Not a header line, treat remaining as body
      bodyStartIndex = i;
      break;
    }
  }

  let body: string | undefined;
  if (bodyStartIndex !== -1 && bodyStartIndex < remainingLines.length) {
    const bodyContent = remainingLines.slice(bodyStartIndex).join("\n").trim();
    if (bodyContent) {
      body = bodyContent;
    }
  }

  return {
    method,
    url,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body,
    rawCode,
  };
}
