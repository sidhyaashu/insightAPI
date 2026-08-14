import asyncio
import os
import sys

sys.path.insert(0, r"c:\Users\ashut\Devlopments\InsightAPI\services\agent-service")
from app.services.chat_service import stream_chat_response

async def test_stream():
    print("Testing stream_chat_response...")
    full = []
    async for token in stream_chat_response([], "Hi, tell me how you can help me with APIs in 2 short bullet points."):
        print(f"CHUNK ({len(token)} chars): {repr(token)}")
        full.append(token)
    print("\n--- FULL RESULT ---")
    print("".join(full))

if __name__ == "__main__":
    asyncio.run(test_stream())
