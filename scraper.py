#!/usr/bin/env python3
import sys, json, asyncio
import re
import xml.etree.ElementTree as ET
from collections import Counter
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

DOMAIN, MAX_PAGES = sys.argv[1], int(sys.argv[2])
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def find_sitemaps(domain):
    robots_url = f"https://{domain}/robots.txt"
    try:
        txt = requests.get(robots_url, headers=HEADERS, timeout=5).text
        hits = re.findall(r"(?im)^sitemap:\s*(https?://\S+)", txt)
        if hits:
            return hits
    except:
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
    except:
        return []

async def main():
    urls = []
    for sm in find_sitemaps(DOMAIN):
        urls += fetch_sitemap_locs(sm)
    urls = list(dict.fromkeys(urls))[:MAX_PAGES]
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
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
    await browser.close()
    freq = Counter(p for page in results for p in page["paragraphs"])
    cleaned = []
    for page in results:
        filtered = [p for p in page["paragraphs"] if p.strip() and freq[p] <= 3]
        page["paragraphs"] = filtered
        cleaned.append(page)
    print(json.dumps({"raw_data": results, "cleaned_data": cleaned}))

if __name__ == "__main__":
    asyncio.run(main())
