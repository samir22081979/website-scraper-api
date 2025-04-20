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
    await run_all(data.domain, max_pages=100)
    
    # Load and enrich the cleaned JSON file
    cleaned = load_cleaned_data("decom_cleaned.json")

    # Attach chatbot_id and user_id to each chunk
    final_chunks = []
    for page in cleaned:
        for paragraph in page["paragraphs"]:
            final_chunks.append({
                "url": page["url"],
                "title": page.get("title", ""),
                "chunk": paragraph,
                "chatbot_id": data.chatbot_id,
                "user_id": data.user_id
            })
    
    return final_chunks
