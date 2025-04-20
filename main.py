@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

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
                    "chatbot_id": data.chatbot_id,
                    "user_id": data.user_id
                })

        return final_chunks

    except Exception as e:
        return {"error": str(e)}
