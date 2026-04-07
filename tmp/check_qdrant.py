"""Verify that threshold=0.25 returns results."""
import asyncio
import os
import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

load_dotenv()

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    query = "Durante cuanto tiempo se detiene el reloj de la plaza en Lurnia"

    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"input": query, "model": "text-embedding-3-small"},
        )
        vec = resp.json()["data"][0]["embedding"]

    client = QdrantClient(host="localhost", port=6333)
    results = client.search(
        collection_name="documents",
        query_vector=vec,
        query_filter=Filter(must=[
            FieldCondition(key="user_id", match=MatchValue(value="42e493b3-6e05-4a31-9777-f81c24c67bd6")),
            FieldCondition(key="topic", match=MatchValue(value="literatura")),
        ]),
        limit=5,
        score_threshold=0.25,
        with_payload=True,
    )
    print(f"Results with threshold=0.25: {len(results)}")
    for r in results:
        print(f"  Score: {r.score:.4f} | {r.payload.get('text', '')[:80]}...")

asyncio.run(main())
