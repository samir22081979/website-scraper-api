from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from scrape_async import run_all, load_cleaned_data

app = FastAPI()

class DomainRequest(BaseModel):
    domain: str

@app.post("/scrape")
async def scrape(request: DomainRequest):
    try:
        cleaned_path = await run_all(request.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        if not isinstance(cleaned, list):
            return {
                "error": f"Expected list but got {type(cleaned)}",
                "raw": cleaned
            }

        final_data = []
        for i, page in enumerate(cleaned):
            if not isinstance(page, dict):
                continue
            paragraphs = page.get("paragraphs", [])
            if not isinstance(paragraphs, list):
                continue

            final_data.append({
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "h1": page.get("h1", []),
                "h2": page.get("h2", []),
                "h3": page.get("h3", []),
                "paragraphs": [p.strip() for p in paragraphs if isinstance(p, str) and p.strip()]
            })

        return {
            "status": "success",
            "pages_scraped": len(final_data),
            "data": final_data[:3]  # return preview
        }

    except Exception as e:
        import traceback
        print("❌ ERROR:")
        print(traceback.format_exc())
        return {"error": str(e)}
