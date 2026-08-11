import asyncio
from app.sdk import AgentEngine

async def test_target(url):
    print(f"\n==========================================")
    print(f"Testing target: {url}")
    print(f"==========================================")
    engine = AgentEngine(headless=True)
    res = await engine.crawl(url, max_pages=6)
    print(f"Summary for {url}:")
    print(f"  Endpoints Discovered: {len(res.captured_endpoints)}")
    print(f"  REST: {res.rest_count} | GraphQL: {res.graphql_count} | WS: {res.websocket_count}")
    print(f"  Pages Explored: {res.explored_count}")
    print(f"  Elapsed Time: {res.elapsed_time_seconds}s")
    print("\n  Sample Endpoints:")
    for ep in res.captured_endpoints:
        print(f"    [{ep.get('method')}] {ep.get('template_route')} ({ep.get('status')})")

async def main():
    await test_target("https://reqres.in")
    await test_target("https://dummyjson.com")
    await test_target("https://petstore.swagger.io")

if __name__ == "__main__":
    asyncio.run(main())
