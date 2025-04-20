from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from scrape_async import run_all, load_cleaned_data

app = FastAPI()

class ScrapeRequest(BaseModel):
    domain: str
    chatbot_id: str
    user_id: str

@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        # Run full scrape
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        print("🧪 CLEANED DATA TYPE:", type(cleaned))
        if isinstance(cleaned, list) and cleaned:
            print("🧪 FIRST ITEM TYPE:", type(cleaned[0]))
            print("🧪 FIRST ITEM VALUE:", cleaned[0])

        final_chunks = []

        for i, page in enumerate(cleaned):
            if not isinstance(page, dict):
                print(f"⚠️ Skipped index {i}: not a dict → {type(page)}")
                continue

            if "paragraphs" not in page or not isinstance(page["paragraphs"], list):
                print(f"⚠️ Skipped index {i}: no valid 'paragraphs'")
                continue

            for paragraph in page["paragraphs"]:
                final_chunks.append({
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "chunk": paragraph,
                    "chatbot_id": data.chatbot_id,
                    "user_id": data.user_id
                })

        if not final_chunks:
            return {"info": "✅ Scraping completed, but no valid paragraphs found."}

        return final_chunks

    except Exception as e:
        import traceback
        print("🔥 Full error traceback:")
        print(traceback.format_exc())
        return {"error": str(e)}
