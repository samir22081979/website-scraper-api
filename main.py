from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import json
import uuid
import os
from typing import List, Dict, Any, Optional
import asyncio
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
from playwright.async_api import async_playwright
import requests
from collections import Counter

app = FastAPI()

# Storage for job status
JOBS = {}
RESULTS_DIR = "scrape_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class ScrapeRequest(BaseModel):
    domain: str
    chatbot_id: str
    user_id: str
    max_pages: int = 100

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total: int
    result_path: Optional[str] = None
    
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ──────────────────────────────────────────────────────────────
# 📌 Sitemap Discovery
def find_sitemaps(domain):
    robots_url = f"https://{domain}/robots.txt"
    try:
        txt = requests.get(robots_url, headers=HEADERS, timeout=5).text
        hits = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", txt)
        if hits:
            return hits
    except Exception:
        pass
    return [f"https://{domain}/sitemap.xml"]

def fetch_sitemap_locs(smap_url):
    try:
        r = requests.get(smap_url, headers=HEADERS, timeout=10)
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
    except Exception as e:
        print(f"⚠️ Error parsing sitemap: {e}")
        return []

# ──────────────────────────────────────────────────────────────
# 🧠 Scrape individual page with Playwright
async def fetch_with_playwright(url, job_id):
    try:
        # Update job status to indicate activity
        JOBS[job_id]["last_url"] = url
        
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
                "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")]
            }
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return {"url": url, "error": str(e)}

# ──────────────────────────────────────────────────────────────
# 🔁 Scrape & Save Raw Data in background
async def process_scrape_job(job_id, domain, max_pages, chatbot_id, user_id):
    try:
        print(f"🔍 Job {job_id}: Crawling website: {domain}")
        JOBS[job_id]["status"] = "finding_sitemaps"
        
        sitemaps = find_sitemaps(domain)
        print(f"Found sitemaps: {sitemaps}")

        all_urls = []
        for sm in sitemaps:
            urls = fetch_sitemap_locs(sm)
            all_urls += urls
            
        # De-duplicate and limit
        all_urls = list(set(all_urls))[:max_pages]
        total_pages = len(all_urls)
        
        JOBS[job_id]["total"] = total_pages
        JOBS[job_id]["status"] = "scraping"
        print(f"📄 Total pages to fetch: {total_pages}")

        results = []
        for i, url in enumerate(all_urls):
            data = await fetch_with_playwright(url, job_id)
            results.append(data)
            
            # Update progress
            JOBS[job_id]["progress"] = i + 1
            
            # Add small delay to prevent overwhelming the system
            await asyncio.sleep(0.1)

        # Save raw results
        raw_file = os.path.join(RESULTS_DIR, f"{job_id}_raw.json")
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"✅ Raw content saved to: {raw_file}")
        
        # Clean data
        JOBS[job_id]["status"] = "cleaning"
        cleaned_path = clean_scraped_data(raw_file, job_id)
        
        # Process into chunks
        JOBS[job_id]["status"] = "chunking"
        final_chunks = process_chunks(cleaned_path, chatbot_id, user_id)
        
        # Save final chunks
        chunks_file = os.path.join(RESULTS_DIR, f"{job_id}_chunks.json")
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(final_chunks, f, ensure_ascii=False, indent=2)
        
        # Update job status to complete
        JOBS[job_id]["status"] = "complete"
        JOBS[job_id]["result_path"] = chunks_file
        
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        print(f"❌ Job {job_id} failed: {e}")

# ──────────────────────────────────────────────────────────────
# 🧹 Clean Data (remove repeated headers/footers)
def clean_scraped_data(raw_path, job_id):
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Find most repeated paragraphs (likely boilerplate)
    all_paragraphs = [p for page in data for p in page.get("paragraphs", [])]
    freq = Counter(all_paragraphs)

    cleaned_data = []
    for page in data:
        unique_paragraphs = []
        for p in page.get("paragraphs", []):
            if p and p.strip() and freq[p] <= 3:  # skip footer-style repeats
                unique_paragraphs.append(p.strip())

        cleaned_data.append({
            "url": page.get("url", ""),
            "title": page.get("title", ""),
            "h1": list(set(page.get("h1", []))),
            "h2": list(set(page.get("h2", []))),
            "h3": list(set(page.get("h3", []))),
            "paragraphs": unique_paragraphs
        })

    out_path = os.path.join(RESULTS_DIR, f"{job_id}_cleaned.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Cleaned content saved to: {out_path}")
    return out_path

# Process data into chunks for the chatbot
def process_chunks(cleaned_path, chatbot_id, user_id):
    with open(cleaned_path, "r", encoding="utf-8") as f:
        cleaned = json.load(f)
        
    final_chunks = []
    for i, page in enumerate(cleaned):
        if not isinstance(page, dict):
            print(f"⚠️ Skipped item {i}: Not a dict → {type(page)}")
            continue
        if "paragraphs" not in page or not isinstance(page["paragraphs"], list):
            print(f"⚠️ Skipped item {i}: Missing or invalid 'paragraphs'")
            continue
        for paragraph in page["paragraphs"]:
            final_chunks.append({
                "url": page.get("url", ""),
                "title": page.get("title", ""),
                "chunk": paragraph,
                "chatbot_id": chatbot_id,
                "user_id": user_id
            })
    return final_chunks

def load_chunks(job_id):
    chunks_file = os.path.join(RESULTS_DIR, f"{job_id}_chunks.json")
    if os.path.exists(chunks_file):
        with open(chunks_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

@app.post("/scrape")
async def scrape(data: ScrapeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "created", 
        "progress": 0,
        "total": 0,
        "domain": data.domain,
        "chatbot_id": data.chatbot_id,
        "user_id": data.user_id
    }
    
    # Start the scraping process in the background
    background_tasks.add_task(
        process_scrape_job, 
        job_id, 
        data.domain, 
        data.max_pages, 
        data.chatbot_id, 
        data.user_id
    )
    
    # Return immediately with the job ID
    return {"job_id": job_id, "status": "processing"}

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "total": job["total"],
        "domain": job["domain"]
    }

@app.get("/results/{job_id}")
async def get_job_results(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_id]
    if job["status"] != "complete":
        return {
            "status": job["status"],
            "progress": job["progress"], 
            "total": job["total"]
        }
    
    chunks = load_chunks(job_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Results not found")
        
    return chunks
