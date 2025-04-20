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
        # Run the full scrape pipeline
        cleaned_path = await run_all(data.domain, max_pages=100)

        # Load and enrich the data
        cleaned = load_cleaned_data(cleaned_path)
        final_chunks = []
        for page in cleaned:
            for paragraph in page.get("paragraphs", []):
                final_chunks.append({
                    "url": page["url"],
                    "title": page.get("title", ""),
                    "chunk": paragraph,
                    "chatbot_id": data.chatbot_id,
                    "user_id": data.user_id
                })

        return final_chunks

    except Exception as e:
        return {"error": str(e)}
