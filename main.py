@app.post("/scrape")
async def scrape(data: ScrapeRequest):
    try:
        cleaned_path = await run_all(data.domain, max_pages=100)
        cleaned = load_cleaned_data(cleaned_path)

        # Check if cleaned is a list
        if not isinstance(cleaned, list):
            return {
                "error": f"load_cleaned_data did not return a list — got {type(cleaned)}",
                "data": cleaned
            }

        # If it's an empty list
        if not cleaned:
            return {"info": "Scraped data is empty", "data": []}

        # Check if first item is a dict with 'paragraphs'
        first_item = cleaned[0]
        return {
            "status": "success",
            "first_item_type": str(type(first_item)),
            "first_item_keys": list(first_item.keys()) if isinstance(first_item, dict) else "Not a dict",
            "first_item_sample": first_item
        }

    except Exception as e:
        import traceback
        print("🔥 Error Traceback:")
        print(traceback.format_exc())
        return {"error": str(e)}
