@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        print("🧪 CLEANED TYPE:", type(cleaned))
        if isinstance(cleaned, list):
            print("🧪 FIRST ITEM TYPE:", type(cleaned[0]) if cleaned else "Empty list")
            print("🧪 FIRST ITEM VALUE:", cleaned[0] if cleaned else "Empty")

        final_chunks = []

        for i, page in enumerate(cleaned):
            if not isinstance(page, dict):
                print(f"⚠️ Skipping index {i}: Not a dict → {type(page)}")
                continue

            if "paragraphs" not in page or not isinstance(page["paragraphs"], list):
                print(f"⚠️ Skipping index {i}: No valid 'paragraphs'")
                continue

            for paragraph in page["paragraphs"]:
                final_chunks.append({
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "chunk": paragraph,
                    "chatbot_id": data.chatbot_id,
                    "user_id": data.user_id
                })

        return final_chunks or {"info": "✅ Scraping done, but no usable content extracted."}

    except Exception as e:
        import traceback
        print("🔥 Full Error Traceback:", traceback.format_exc())
        return {"error": str(e)}
