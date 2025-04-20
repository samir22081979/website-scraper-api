@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        print("🔍 Type of cleaned:", type(cleaned))
        print("🔍 Sample cleaned data (first item):", cleaned[0] if cleaned else "Empty")

        return {"preview": cleaned[:2]}  # Just return raw data for now

    except Exception as e:
        import traceback
        print("🔥 Error Traceback:")
        print(traceback.format_exc())
        return {"error": str(e)}
