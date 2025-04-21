# Website Scraper & Cleaner API

This FastAPI app scrapes a website using Playwright and returns raw and cleaned data.

## Files

- `main.py`: FastAPI application.
- `requirements.txt`: Python dependencies.
- `start.sh`: Installs Playwright browsers and starts the server.
- `README.md`: This file.

## Local Testing

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```
2. Run the API:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
3. Test with:
   ```bash
   curl -X POST http://localhost:8000/scrape -H "Content-Type: application/json" -d '{"domain":"decomengineering.co.uk","max_pages":10}'
   ```

## Railway Deployment

1. Create a new project on Railway and connect this repo (or upload files).
2. Railway auto-detects Python and installs dependencies via `requirements.txt`.
3. Set the **Start Command** in Railway:
   ```
   bash start.sh
   ```
4. Deploy. After deployment, the endpoint will be:
   ```
   https://<your-railway-domain>/scrape
   ```
5. Connect this endpoint in n8n via an **HTTP Request** node:
   - Method: `POST`
   - URL: `https://<your-railway-domain>/scrape`
   - Body Type: JSON
   - Body:
     ```json
     { "domain": "decomengineering.co.uk", "max_pages": 100 }
     ```
