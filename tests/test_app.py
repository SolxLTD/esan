import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ADMIN_PASSWORD"] = "pw"
os.environ["SECRET_KEY"] = "test"
os.environ["BUSINESS_WHATSAPP"] = "2348000000000"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_legacy_training_title_migrates(tmp_path):
    from sqlmodel import Session, SQLModel, create_engine, select

    from app.main import migrate_training_titles
    from app.models import Training

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-training.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Training(
            title="Weed, Pest & Disease Management for Maize and Vegetables",
            description="Legacy course",
            duration="2 days",
            price=20000,
        ))
        session.commit()
        migrate_training_titles(session)
        migrated = session.exec(select(Training)).one()
        assert migrated.title == "Weed, Pest & Disease Management for Crops"
        assert migrated.description.startswith("Identifying common crop problems")
    engine.dispose()


def test_flow(tmp_path, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "PRODUCT_PHOTO_DIR", tmp_path / "product-photos")
    with main.engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS productphoto "
            "(id INTEGER PRIMARY KEY, product_id INTEGER, image_path VARCHAR, alt_text VARCHAR)"
        )
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        for page_url in ("/", "/product/1", "/training", "/training/field-guide", "/register", "/admin/login"):
            page_response = c.get(page_url)
            assert page_response.status_code == 200
            assert '/static/style.css?v=7' in page_response.text
            assert 'class="site-background-video"' in page_response.text
            assert 'src="/static/background-video.mp4" type="video/mp4"' in page_response.text
            assert 'class="brand logo-pill"' in page_response.text
            assert 'href="/training">Training</a>' in page_response.text
            assert 'class="whatsapp-float"' in page_response.text
        assert 'href="https://www.instagram.com/esanfarmers?cplk=MThkMGdkaGQyeG1tNQ=="' in page_response.text
        assert 'href="https://www.facebook.com/share/1CdiZ8TFv9/"' in page_response.text
        assert 'href="https://www.threads.com/@esanfarming"' in page_response.text
        assert 'aria-label="Follow Esan Farmers on Instagram"' in page_response.text
        assert 'aria-label="Follow Esan Farmers on Facebook"' in page_response.text
        assert 'aria-label="Follow Esan Farmers on Threads"' in page_response.text
        assert "Facebook · Coming soon" not in page_response.text
        assert "https://wa.me/2348000000000?text=" in page_response.text
        site_styles = c.get("/static/style.css").text
        assert "position:sticky;top:12px;z-index:10" in site_styles
        assert ".site-header.is-scrolled" in site_styles
        assert ".site-header.is-scrolled{background:transparent" in site_styles
        assert "max-width:820px" in site_styles
        assert c.get("/static/header.js").status_code == 200
        assert 'header.classList.toggle("is-scrolled"' in c.get("/static/header.js").text
        assert "@keyframes order-button-shine" in c.get("/static/style.css").text
        background_css = c.get("/static/style.css").text
        assert "/static/images/farm-hero.svg" not in background_css
        assert "background:#f2f6ec" in background_css
        assert "@media(max-width:960px)" in background_css
        assert c.get("/").status_code == 200
        product_page = c.get("/product/1")
        assert product_page.status_code == 200
        assert "Product description" in product_page.text
        assert "Order now on WhatsApp" in product_page.text
        assert "₦6,500" not in product_page.text
        assert c.get("/training").status_code == 200
        training_page = c.get("/training")
        assert "field guide" in training_page.text.lower()
        assert "youtube.com" in training_page.text
        assert "QUICK VISUAL LESSONS" in training_page.text
        assert 'src="/static/images/training/training-session.png"' in training_page.text
        assert training_page.text.count('src="/static/images/training/field-training.jpeg"') == 3
        assert 'src="/static/images/training/environment-care.jpg"' in training_page.text
        assert 'src="/static/images/training/farmer-workshop.jpg" alt="Farmer examining an agricultural product during a group training session"' in training_page.text
        assert 'src="/static/images/services/office-fumigation.jpg" alt="Worker wearing protective clothing inside a large indoor facility"' in training_page.text
        assert c.get("/static/images/training/farmer-workshop.jpg").status_code == 200
        assert c.get("/static/images/services/office-fumigation.jpg").status_code == 200
        assert 'src="/static/images/training/crop-pest-management.jpeg"' in training_page.text
        assert 'src="/static/images/training/fertilizer-program.jpg"' in training_page.text
        assert "Farm worker wearing a protective suit, goggles, gloves and respirator" in training_page.text
        assert "Weed, Pest &amp; Disease Management for Crops" in training_page.text
        assert "Weed, Pest &amp; Disease Management for Maize and Vegetables" not in training_page.text
        assert "Protect waterways and beneficial organisms" in training_page.text
        assert "locked away from children, food, feed and water" in training_page.text
        assert "₦10,000" not in training_page.text
        assert "₦20,000" not in training_page.text
        assert "₦12,000" not in training_page.text
        assert "Four steps to safer handling" in training_page.text
        assert "Seminars and field sessions" in training_page.text
        assert training_page.text.count('class="chemical-step reveal-on-scroll"') == 4
        assert training_page.text.count('class="seminar-photo reveal-on-scroll"') == 3
        for image in (
            "farm-hero.svg",
            "food-production.svg",
            "safe-farming.svg",
            "fumigation-service.svg",
            "product-samples/fipronil-100-sc.jpeg",
            "product-samples/imidacloprid-20-sl.jpeg",
            "product-samples/agrochemical-assortment.jpeg",
            "services/farm-fumigation.jpg",
            "services/home-fumigation.jpg",
            "services/office-fumigation.jpg",
            "services/food-production.jpg",
            "training/training-session.png",
            "training/classroom-training.jpeg",
            "training/farm-training.jpeg",
            "training/safe-application.jpeg",
            "training/field-training.jpeg",
            "training/farmer-workshop.jpg",
            "training/crop-demonstration.jpg",
            "training/environment-care.jpg",
            "training/safe-storage.jpeg",
            "training/crop-pest-management.jpeg",
            "training/fertilizer-program.jpg",
        ):
            assert c.get(f"/static/images/{image}").status_code == 200
        background_video = c.get("/static/background-video.mp4")
        assert background_video.status_code == 200
        assert background_video.headers["content-type"].startswith("video/mp4")
        assert c.get("/static/training.js").status_code == 200
        assert c.get("/static/slideshow.js").status_code == 200
        home_page = c.get("/")
        assert "Food production" in home_page.text
        assert 'class="quick-links"' in home_page.text
        assert 'href="#shop"' in home_page.text
        assert "Explore fumigation" in home_page.text
        assert "Build farm skills" in home_page.text
        assert "Benin-Auchi Express Way, Benin City, Edo State" in home_page.text
        assert "+234 806 584 3125" in home_page.text
        assert "Esanfarmer@gmail.com" in home_page.text
        assert "Farm fumigation" in home_page.text and "Home fumigation" in home_page.text
        assert home_page.text.count('data-carousel-slide') == 7
        assert "₦10,000" not in home_page.text
        assert "₦20,000" not in home_page.text
        assert "₦12,000" not in home_page.text
        assert 'src="/static/images/farm-hero.svg"' not in home_page.text
        assert 'src="/static/images/food-production.svg"' not in home_page.text
        assert 'src="/static/images/safe-farming.svg"' not in home_page.text
        assert home_page.text.count('class="service-photo-grid"') == 1
        assert home_page.text.count('alt="Farm worker spraying crops in a field"') == 2
        service_photos = home_page.text.split('<div class="service-photo-grid">', 1)[1].split("</div>", 1)[0]
        assert "<figcaption>" not in service_photos
        assert home_page.text.count('class="sample-card"') == 3
        assert c.get("/training/field-guide").status_code == 200
        assert c.get("/register").status_code == 200
        assert c.get("/?q=glyphosate").status_code == 200
        r = c.post("/order/1", data={"customer_name": "Ade", "phone": "08031234567", "qty": 2}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("https://wa.me/2348000000000")
        assert c.post("/order/1", data={"customer_name": "Ade", "phone": "12", "qty": 1}).status_code == 400
        r = c.post("/register/1", data={"customer_name": "Ade", "phone": "08031234567"}, follow_redirects=False)
        assert r.status_code == 303
        r = c.post("/register", data={
            "full_name": "Ada Farmer",
            "phone": "08031234567",
            "email": "ada@example.com",
            "interest": "Food production",
        }, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/register?submitted=true"
        assert c.post("/register", data={"full_name": "Invalid", "phone": "12"}).status_code == 400
        assert c.get("/admin", follow_redirects=False).status_code == 303
        assert c.post("/admin/login", data={"password": "bad"}).status_code == 401
        assert c.post("/admin/login", data={"password": "pw"}, follow_redirects=False).status_code == 303
        page = c.get("/admin")
        assert page.status_code == 200 and "Ade" in page.text and "Ada Farmer" in page.text
        assert c.post(
            "/admin/products/1/photos",
            files=[("photos", (f"photo-{i}.png", b"\x89PNG\r\n\x1a\nphoto-data", "image/png")) for i in range(2)],
            follow_redirects=False,
        ).status_code == 400
        photo_response = c.post(
            "/admin/products/1/photos",
            files=[("photos", (f"photo-{i}.png", b"\x89PNG\r\n\x1a\nphoto-data", "image/png")) for i in range(3)],
            follow_redirects=False,
        )
        assert photo_response.status_code == 303
        product_page = c.get("/product/1")
        assert product_page.text.count('class="product-gallery"') == 1
        assert product_page.text.count("<img src=\"/static/products/") == 3
        assert main.inspect(main.engine).get_columns("productphoto")[-1]["name"] == "public_id"
        cloud_uploads = []
        cloud_deletions = []

        def fake_cloud_upload(content, **kwargs):
            public_id = f"esan-farmers/products/{len(cloud_uploads)}"
            cloud_uploads.append((content, kwargs))
            return {
                "secure_url": f"https://res.cloudinary.com/test/image/upload/{public_id}.png",
                "public_id": public_id,
            }

        monkeypatch.setattr(main, "CLOUDINARY_URL", "cloudinary://test-key:test-secret@test-cloud")
        monkeypatch.setattr(main.cloudinary_uploader, "upload", fake_cloud_upload)
        monkeypatch.setattr(
            main.cloudinary_uploader,
            "destroy",
            lambda public_id, **kwargs: cloud_deletions.append(public_id) or {"result": "ok"},
        )
        cloud_response = c.post(
            "/admin/products/1/photos",
            files=[("photos", (f"cloud-{i}.png", b"\x89PNG\r\n\x1a\nphoto-data", "image/png")) for i in range(3)],
            follow_redirects=False,
        )
        assert cloud_response.status_code == 303
        assert len(cloud_uploads) == 3
        assert all(upload[1]["folder"] == "esan-farmers/products" for upload in cloud_uploads)
        assert len(cloud_deletions) == 0
        product_page = c.get("/product/1")
        assert product_page.text.count(
            '<img src="https://res.cloudinary.com/test/image/upload/'
        ) == 3
        assert c.post("/admin/orders/1/status", data={"status": "confirmed"}, follow_redirects=False).status_code == 303
        assert c.post("/admin/products/1/stock", follow_redirects=False).status_code == 303
        assert c.get("/admin/products").status_code == 200
        assert c.post("/admin/products/1/delete", follow_redirects=False).status_code == 303
        assert cloud_deletions == [f"esan-farmers/products/{i}" for i in range(3)]
