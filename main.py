# main.py
import re, json, xml.etree.ElementTree as ET
from collections import Counter
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
browser = None  # global browser instance

class ScrapeRequest(BaseModel):
    domain: str
    max_pages: int = 100

@app.get("/healthz")
async def healthz():
    # Pure Python, no Playwright/bs4 import
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    # Only here do we import and launch Playwright once per container
    from playwright.async_api import async_playwright
    p = await async_playwright().start()
    global browser
    browser = await p.chromium.launch(headless=True)

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    # Light imports only when needed
    import requests
    from bs4 import BeautifulSoup

    DOMAIN, MAX_PAGES = request.domain, request.max_pages

    # 1) Find sitemaps (requests only)
    def find_sitemaps(domain):
        try:
            txt = requests.get(f"https://{domain}/robots.txt", timeout=5).text
            return re.findall(r"(?im)^sitemap:\s*(https?://\S+)", txt) or [f"https://{domain}/sitemap.xml"]
        except:
            return [f"https://{domain}/sitemap.xml"]

    # 2) Collect URLs (requests only)
    def fetch_sitemap_locs(url):
        # … your ET/requests logic …
        return []

    urls = []
    for sm in find_sitemaps(DOMAIN):
        urls += fetch_sitemap_locs(sm)
    urls = list(dict.fromkeys(urls))[:MAX_PAGES]

    # 3) Scrape pages via the already‑running browser
    results = []
    for url in urls:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        html = await page.content()
        await page.close()
        soup = BeautifulSoup(html, "lxml")
        results.append({
            "url": url,
            "title": soup.title.string.strip() if soup.title else "",
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
            "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
            "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")],
        })

    # 4) Clean data
    freq = Counter(p for page in results for p in page["paragraphs"])
    cleaned = [
        {
          **{k: v for k, v in page.items() if k != "paragraphs"},
          "paragraphs": [p for p in page["paragraphs"] if p.strip() and freq[p] <= 3]
        }
        for page in results
    ]

    return {"raw_data": results, "cleaned_data": cleaned}
