<p align="center"><img src="assets/logo.png" alt="Esan Farmer" width="220"></p>

# Esan Farmers

Agrochemical shop and farmer-training site for Esan, Edo State. Farmers browse products with label and NAFDAC details, order or register for training, and the request is saved in the database and handed to WhatsApp. The owner manages everything from `/admin`.

## How the pieces fit

| Part | What it is | Where |
|---|---|---|
| **Backend + site** | FastAPI app that serves the pages, saves orders and registrations, and runs the admin | `app/` |
| **Database** | SQLite locally, Postgres in production (`DATABASE_URL`) | `app/models.py` |
| **Demo page** | Static phone preview with sample data, no backend. Free to host on GitHub Pages | `docs/index.html` |
| **Logo** | Source logo, plus favicon and app icon used by the site | `assets/`, `app/static/` |

The demo page and the app look alike on purpose, but they are separate: the demo has fixed sample data, while the app reads and writes the database. Deploy the app for real customers; use the demo only to show the idea.

## Run locally
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ADMIN_PASSWORD=yourpass BUSINESS_WHATSAPP=234XXXXXXXXXX uvicorn app.main:app --reload
pytest
```

## Deploy (Render + Neon Postgres)
1. Create a free Postgres database on neon.tech and copy its connection string.
2. On render.com choose New > Blueprint and pick this repo (uses `render.yaml`).
3. Set `DATABASE_URL`, `ADMIN_PASSWORD`, `BUSINESS_WHATSAPP`. `SECRET_KEY` is generated.
4. Open `/admin/login` and replace the sample products with real stock.

## Demo on GitHub Pages
Repo Settings > Pages > Deploy from branch > `main` and folder `/docs`.

## Before launch
- Replace sample products, prices and NAFDAC numbers in `app/seed.py` (or via `/admin/products`)
- Never commit `.env` or a real password; keep secrets in Render's environment settings
