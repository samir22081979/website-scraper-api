from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from scrape_async import run_all, load_cleaned_data

app = FastAPI()

# 🧩 Input data model
class ScrapeRequest(BaseModel):
    domain: str
    chatbot_id: str
    user_id: str

# 🔍 Endpoint to trigger scraping
@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        # 1. Run full scraping pipeline
        cleaned_path = await run_all(data.domain, max_pages=100)

        # 2. Load cleaned JSON content
        cleaned = load_cleaned_data(cleaned_path)

        # ✅ Check data format
        if not isinstance(cleaned, list):
            return {
                "error": f"Expected a list from load_cleaned_data, got {type(cleaned)}",
                "data": cleaned
            }

        # 3. Prepare enriched paragraph chunks
        final_chunks = []
        for i, page in enumerate(cleaned):
            if not isinstance(page, dict):
                print(f"⚠️ Skipping index {i} — not a dict")
                continue

            paragraphs = page.get("paragraphs")
            if not isinstance(paragraphs, list):
                print(f"⚠️ Skipping index {i} — missing or invalid 'paragraphs'")
                continue

            for p in paragraphs:
                if not isinstance(p, str) or not p.strip():
                    continue  # skip empty or bad strings

                final_chunks.append({
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "chunk": p.strip(),
                    "chatbot_id": data.chatbot_id,
                    "user_id": data.user_id
                })

        # 4. Return preview to confirm it works
        return {
            "status": "success",
            "total_chunks": len(final_chunks),
            "sample": final_chunks[:2]
        }

    except Exception as e:
        import traceback
        print("🔥 ERROR TRACEBACK:")
        print(traceback.format_exc())
        return {"error": str(e)}
