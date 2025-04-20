from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from scrape_async import run_all, load_cleaned_data

app = FastAPI()

# ✅ This was missing!
class ScrapeRequest(BaseModel):
    domain: str
    chatbot_id: str
    user_id: str

@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        if not isinstance(cleaned, list):
            return {
                "error": f"load_cleaned_data did not return a list — got {type(cleaned)}",
                "data": cleaned
            }

        if not cleaned:
            return {"info": "Scraped data is empty", "data": []}

        first_item = cleaned[0]
        return {
            "status": "success",
            "first_item_type": str(type(first_item)),
            "first_item_keys": list(first_item.keys()) if isinstance(first_item, dict) else "Not a dict",
            "first_item_sample": first_item
        }

    except Exception as e:
        import traceback
        print("🔥 Error Traceback:")
        print(traceback.format_exc())
        return {"error": str(e)}
