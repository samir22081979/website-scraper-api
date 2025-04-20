import re
import json
import argparse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import Counter
from playwright.sync_api import sync_playwright

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

def scrape_url(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            content = page.content()
            browser.close()
        soup = BeautifulSoup(content, "lxml")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        return paragraphs
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return []

def clean_paragraphs(paragraph_lists, threshold=3):
    flat = [p for lst in paragraph_lists for p in lst]
    freq = Counter(flat)
    return [[p for p in lst if p and freq[p] <= threshold] for lst in paragraph_lists]

def run(domain, chatbot_id, user_id, output_path="/tmp/output.json"):
    print(f"🔍 Starting scrape for: {domain}")
    sitemaps = find_sitemaps(domain)
    all_urls = []
    for sm in sitemaps:
        all_urls += fetch_sitemap_locs(sm)
    all_urls = list(set(all_urls))[:50]

    print(f"📄 Found {len(all_urls)} pages.")

    all_paragraphs = []
    for url in all_urls:
        paras = scrape_url(url)
        all_paragraphs.append(paras)

    cleaned_lists = clean_paragraphs(all_paragraphs)
    combined = []

    for i in range(len(all_urls)):
        for chunk in cleaned_lists[i]:
            combined.append({
                "url": all_urls[i],
                "chunk": chunk,
                "chatbot_id": chatbot_id,
                "user_id": user_id
            })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"✅ Done. Cleaned data saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--chatbot_id", required=True)
    parser.add_argument("--user_id", required=True)
    args = parser.parse_args()

    run(args.domain, args.chatbot_id, args.user_id)