import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ADMIN_PASSWORD"] = "pw"
os.environ["SECRET_KEY"] = "test"
os.environ["BUSINESS_WHATSAPP"] = "2348000000000"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


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
        for image in (
            "farm-hero.svg",
            "food-production.svg",
            "safe-farming.svg",
            "fumigation-service.svg",
            "product-samples/fipronil-100-sc.jpeg",
            "product-samples/imidacloprid-20-sl.jpeg",
            "product-samples/agrochemical-assortment.jpeg",
        ):
            assert c.get(f"/static/images/{image}").status_code == 200
        home_page = c.get("/")
        assert "Food production" in home_page.text
        assert "Indoor fumigation" in home_page.text and "Outdoor fumigation" in home_page.text
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
