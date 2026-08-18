import { repairStreamingMarkdown, isSafeUrl, parseHttpSnippet } from "../src/components/markdown/markdown-utils.ts";

let passed = 0;
let failed = 0;

function assert(condition, name) {
  if (condition) {
    console.log(`✓ ${name}`);
    passed++;
  } else {
    console.error(`✗ ${name}`);
    failed++;
  }
}

console.log("=== Running Markdown System Verification Tests ===\n");

// 1. Streaming Markdown Repair Tests
const incompleteCode = "Here is some code:\n```typescript\nconst a = 1;";
const repairedCode = repairStreamingMarkdown(incompleteCode, true);
assert(repairedCode.endsWith("\n```"), "Repairs unclosed code fence during streaming");

const completeCode = "```typescript\nconst a = 1;\n```";
assert(repairStreamingMarkdown(completeCode, true) === completeCode, "Leaves closed code fence intact");

const incompleteMath = "Formula: $$\nE = mc^2";
const repairedMath = repairStreamingMarkdown(incompleteMath, true);
assert(repairedMath.endsWith("\n$$"), "Repairs unclosed block math during streaming");

// 2. Safe URL Sanitization Tests
assert(isSafeUrl("https://api.example.com/v1/users"), "Allows https:// URLs");
assert(isSafeUrl("http://localhost:8080/api"), "Allows http:// URLs");
assert(isSafeUrl("/dashboard/analytics"), "Allows relative URLs");
assert(isSafeUrl("#heading-1"), "Allows anchor links");
assert(isSafeUrl("mailto:support@insightapi.ai"), "Allows mailto: links");
assert(!isSafeUrl("javascript:alert(1)"), "Blocks dangerous javascript: URLs");
assert(!isSafeUrl("vbscript:msgbox(1)"), "Blocks vbscript: URLs");
assert(!isSafeUrl("data:text/html,<script>alert(1)</script>"), "Blocks unsafe data: URLs");
assert(!isSafeUrl(undefined), "Blocks undefined URLs");

// 3. HTTP Snippet Parsing Tests
const getSnippet = "GET https://api.bseindia.com/BseIndiaAPI/api/GetStkCurr/w?str={query}";
const parsedGet = parseHttpSnippet(getSnippet);
assert(parsedGet !== null && parsedGet.method === "GET", "Correctly parses GET endpoint");
assert(parsedGet?.url === "https://api.bseindia.com/BseIndiaAPI/api/GetStkCurr/w?str={query}", "Correctly extracts endpoint URL");

const postSnippet = `POST /api/v1/users\nContent-Type: application/json\nAuthorization: Bearer token123\n\n{\n  "name": "Ashutosh"\n}`;
const parsedPost = parseHttpSnippet(postSnippet);
assert(parsedPost !== null && parsedPost.method === "POST", "Correctly parses POST endpoint");
assert(parsedPost?.headers?.["Content-Type"] === "application/json", "Correctly parses request headers");
assert(parsedPost?.body?.includes('"name": "Ashutosh"'), "Correctly parses request JSON body");

console.log(`\n=== Verification Results: ${passed} Passed, ${failed} Failed ===`);

if (failed > 0) {
  process.exit(1);
}
