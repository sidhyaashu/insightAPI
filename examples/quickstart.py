"""
quickstart.py — End-to-End Usage Example for InsightAPI AI (v1.0.0)

Demonstrates:
1. Importing AgentEngine from insightapi SDK
2. Running a goal-directed autonomous crawl
3. Retrieving captured endpoints & LLM cost metrics
4. Exporting OpenAPI 3.0, Postman, and Markdown documentation
"""
import asyncio
from insightapi import AgentEngine


async def main():
    print("🚀 InsightAPI AI v1.0.0 — Quickstart Demo\n")

    # 1. Initialize Engine
    engine = AgentEngine(headless=True)

    # 2. Run Goal-Directed Crawl
    target_url = "https://httpbin.org"
    print(f"Starting autonomous crawl on: {target_url}")

    result = await engine.crawl(
        url=target_url,
        max_pages=5,
        goal="Discover all JSON data returning endpoints",
        parallel=False,
    )

    # 3. Print Results & LLM Spend Metrics
    print("\n✅ Crawl Completed Successfully!")
    print(f"Session ID           : {result.session_id}")
    print(f"Target URL           : {result.target_url}")
    print(f"Explored Pages       : {result.explored_count}")
    print(f"Endpoints Captured   : {len(result.captured_endpoints)}")
    print(f"REST API Count       : {result.rest_count}")
    print(f"GraphQL Ops Count    : {result.graphql_count}")
    print(f"Elapsed Time         : {result.elapsed_time_seconds:.2f} seconds")

    if result.llm_metrics:
        print("\n💰 LLM Spend & Usage Metrics:")
        print(f"  - Tokens Used      : {result.llm_metrics.get('tokens_used', 0)}")
        print(f"  - LLM Calls Made   : {result.llm_metrics.get('llm_calls_made', 0)}")
        print(f"  - Estimated USD    : ${result.llm_metrics.get('estimated_cost_usd', 0.0):.4f}")

    # 4. Export OpenAPI 3.0 Spec
    print("\n📄 OpenAPI 3.0 Spec Preview (first 25 lines):")
    openapi_json = result.to_openapi()
    for line in openapi_json.splitlines()[:25]:
        print(f"  {line}")


if __name__ == "__main__":
    asyncio.run(main())
