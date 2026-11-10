<p align="center"><img src="assets/logo.png" alt="Esan Farmer" width="220"></p>

# Esan Farmers

Food-production, agrochemical and environmental-services website for Esan, Edo State. Farmers can browse products, register as members, sign up for training, and use the online field guide and video-training links. Orders and course bookings are saved in the database and handed to WhatsApp. The owner manages orders, course bookings, members and products from `/admin`.

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

## Product photos
Upload 3–5 PNG, JPEG or WebP photos per product from `/admin/products`. Without Cloudinary, files are saved in `app/static/products/`. With Cloudinary configured, photo files go to Cloudinary and their secure URLs and Cloudinary public IDs are saved in the `ProductPhoto` database table. Existing photo records are migrated to include the public ID column when the app starts.

The homepage's **Product Samples** gallery uses illustrative photos from `chemicals/`; these are not linked to specific product listings or a live stock count. To show photos on an individual product page, upload that product's photos from `/admin/products`.

### Connect Cloudinary
1. Create a Cloudinary account and open the **Dashboard**.
2. Copy the full `CLOUDINARY_URL` value shown in the dashboard. It contains your cloud name, API key and API secret; keep it private.
3. For local testing, add the value to your untracked `.env` file as `CLOUDINARY_URL=...`, then start the app with `uvicorn app.main:app --reload --env-file .env`. Or set the `CLOUDINARY_URL` environment variable in your terminal before starting the app.
4. For Render, open your web service **Environment** settings, add `CLOUDINARY_URL` with the dashboard value, and save/redeploy. Do not put credentials in source code or commit them.
5. Sign in at `/admin`, open **Manage products**, and upload 3–5 photos for each product. The app uploads them to the `esan-farmers/products` Cloudinary folder. Replacing photos or deleting a product also removes the old Cloudinary images.

If `CLOUDINARY_URL` is empty, the app continues to store uploaded images locally. Render's ordinary filesystem is not durable across deploys, so configure Cloudinary before uploading production product photos.

## Demo on GitHub Pages
Repo Settings > Pages > Deploy from branch > `main` and folder `/docs`.

## Before launch
- Replace sample products, prices and NAFDAC numbers in `app/seed.py` (or via `/admin/products`)
- Set `TRAINING_YOUTUBE_URL` to the company’s YouTube channel or playlist URL; until configured, the training page links to a YouTube search for Esan Farmers lessons
- Never commit `.env` or a real password; keep secrets in Render's environment settings
