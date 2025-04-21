import re
import json
import asyncio
import xml.etree.ElementTree as ET
from collections import Counter
from bs4 import BeautifulSoup
import requests
from playwright.async_api import async_playwright
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class ScrapeRequest(BaseModel):
    domain: str
    max_pages: int = 100

app = FastAPI()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def find_sitemaps(domain):
    robots_url = f"https://{domain}/robots.txt"
    try:
        txt = requests.get(robots_url, headers={"User-Agent": HEADERS}).text
        hits = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", txt)
        if hits:
            return hits
    except Exception:
        pass
    return [f"https://{domain}/sitemap.xml"]

def fetch_sitemap_locs(smap_url):
    try:
        r = requests.get(smap_url, headers={"User-Agent": HEADERS}, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        if root.tag.endswith("sitemapindex"):
            out = []
            for sm in root.findall("sm:sitemap", ns):
                loc = sm.find("sm:loc", ns).text
                out += fetch_sitemap_locs(loc)
            return out
        return [u.text for u in root.findall("sm:url/sm:loc", ns)]
    except Exception:
        return []

async def fetch_with_playwright(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            content = await page.content()
            await browser.close()
            soup = BeautifulSoup(content, "lxml")
            return {
                "url": url,
                "title": soup.title.string.strip() if soup.title else "",
                "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
                "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
                "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
                "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")],
            }
    except Exception as e:
        return {"url": url, "error": str(e)}

async def crawl_website(domain, max_pages=100):
    sitemaps = find_sitemaps(domain)
    all_urls = []
    for sm in sitemaps:
        all_urls += fetch_sitemap_locs(sm)
    all_urls = list(set(all_urls))[:max_pages]
    results = []
    for url in all_urls:
        data = await fetch_with_playwright(url)
        results.append(data)
    return results

def clean_data(data):
    all_paragraphs = [p for page in data for p in page.get("paragraphs", [])]
    freq = Counter(all_paragraphs)
    cleaned = []
    for page in data:
        unique_paragraphs = [p for p in page.get("paragraphs", []) if p.strip() and freq[p] <= 3]
        cleaned.append({
            "url": page.get("url", ""),
            "title": page.get("title", ""),
            "h1": list(set(page.get("h1", []))),
            "h2": list(set(page.get("h2", []))),
            "h3": list(set(page.get("h3", []))),
            "paragraphs": unique_paragraphs,
        })
    return cleaned

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        raw = await crawl_website(request.domain, request.max_pages)
        cleaned = clean_data(raw)
        return {"raw_data": raw, "cleaned_data": cleaned}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
