"""
cli.py — InsightAPI Command-Line Interface.

Architecture (AGENTS.md §21 / Phase 15):
  CLI uses the exact same InvestigationRuntime as HTTP and WebSocket paths.
  Usage:
    python -m app.cli investigate https://target-app.com --max-pages 5 --output-dir ./artifacts
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from typing import Dict, List, Optional

from app.runtime.service import InvestigationRequest, runtime_service


def _parse_headers(header_args: Optional[List[str]]) -> Dict[str, str]:
    """Parse list of 'Key: Value' strings into a dictionary."""
    headers: Dict[str, str] = {}
    if not header_args:
        return headers
    for h in header_args:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


async def _run_investigation(args: argparse.Namespace) -> None:
    session_id = args.session_id or f"cli-{uuid.uuid4().hex[:8]}"
    auth_headers = _parse_headers(args.header)

    request = InvestigationRequest(
        session_id=session_id,
        target_url=args.target_url,
        goal_description=args.goal or f"CLI Autonomous discovery of {args.target_url}",
        auth_headers=auth_headers,
        max_pages=args.max_pages,
        max_tool_calls=args.max_tool_calls,
        max_runtime_seconds=args.max_runtime_seconds,
    )

    print(f"\n=======================================================")
    print(f" InsightAPI Autonomous Agent Investigation Runtime")
    print(f" Target URL : {request.target_url}")
    print(f" Session ID : {request.session_id}")
    print(f" Max Pages  : {request.max_pages}")
    print(f"=======================================================\n")

    summary_data = None
    async for event in runtime_service.stream_investigation(request):
        event_type = event.get("type")
        if event_type == "tool_start":
            print(f"[*] [START] {event.get('title', event.get('tool'))}")
        elif event_type == "tool_result":
            status = event.get("status", "unknown").upper()
            latency = event.get("latency_ms", 0)
            print(f"    [+] [{status}] Latency: {latency}ms")
        elif event_type == "approval_required":
            action = event.get("action", {})
            print(f"\n[!] [APPROVAL REQUIRED] Destructive action: {action.get('action_type')} on {action.get('target')}")
        elif event_type == "token":
            sys.stdout.write(event.get("content", ""))
            sys.stdout.flush()
        elif event_type == "done":
            summary_data = event.get("summary", {})

    print(f"\n\n=======================================================")
    print(f" Investigation Completed")
    if summary_data:
        print(f" Discovered Endpoints : {summary_data.get('discovered_count', 0)}")
        print(f" Verified with Evidence: {summary_data.get('verified_count', 0)}")
        print(f" Application Graph Nodes: {summary_data.get('graph_size', 0)}")
    print(f"=======================================================\n")

    # Export artifacts
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        artifacts = await runtime_service.get_artifacts(session_id)

        openapi_path = os.path.join(args.output_dir, "openapi.json")
        with open(openapi_path, "w", encoding="utf-8") as f:
            json.dump(artifacts.get("openapi_spec", {}), f, indent=2)

        postman_path = os.path.join(args.output_dir, "postman_collection.json")
        with open(postman_path, "w", encoding="utf-8") as f:
            json.dump(artifacts.get("postman_collection", {}), f, indent=2)

        report_path = os.path.join(args.output_dir, "discovery_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(artifacts.get("discovery_report", "# Discovery Report"))

        print(f"[+] Saved artifacts to: {os.path.abspath(args.output_dir)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insightapi",
        description="InsightAPI Autonomous API Discovery CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # investigate subcommand
    inv_parser = subparsers.add_parser("investigate", help="Run autonomous API discovery on a target URL")
    inv_parser.add_argument("target_url", type=str, help="Target application URL (e.g. https://api.example.com)")
    inv_parser.add_argument("--goal", type=str, default=None, help="Custom investigation goal or instruction")
    inv_parser.add_argument("--session-id", type=str, default=None, help="Custom session ID")
    inv_parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages/routes to explore (default: 10)")
    inv_parser.add_argument("--max-tool-calls", type=int, default=50, help="Maximum tool call budget (default: 50)")
    inv_parser.add_argument("--max-runtime-seconds", type=int, default=600, help="Maximum runtime budget in seconds (default: 600)")
    inv_parser.add_argument("-H", "--header", action="append", help="Authentication header, e.g. 'Authorization: Bearer <token>'")
    inv_parser.add_argument("-o", "--output-dir", type=str, default="./artifacts", help="Directory to save generated artifacts (default: ./artifacts)")

    args = parser.parse_args()
    if args.command == "investigate":
        asyncio.run(_run_investigation(args))


if __name__ == "__main__":
    main()
