from fastapi import FastAPI, Request
from pydantic import BaseModel
from scrape_and_clean import run

app = FastAPI()

class ScrapeRequest(BaseModel):
    domain: str
    chatbot_id: str
    user_id: str

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    run(
        domain=request.domain,
        chatbot_id=request.chatbot_id,
        user_id=request.user_id,
        output_path="/tmp/output.json"
    )
    with open("/tmp/output.json", "r", encoding="utf-8") as f:
        return f.read()