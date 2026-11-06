import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ADMIN_PASSWORD"] = "pw"
os.environ["SECRET_KEY"] = "test"
os.environ["BUSINESS_WHATSAPP"] = "2348000000000"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def test_flow():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert c.get("/").status_code == 200
        assert c.get("/product/1").status_code == 200
        assert c.get("/training").status_code == 200
        assert c.get("/?q=glyphosate").status_code == 200
        r = c.post("/order/1", data={"customer_name": "Ade", "phone": "08031234567", "qty": 2}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("https://wa.me/2348000000000")
        assert c.post("/order/1", data={"customer_name": "Ade", "phone": "12", "qty": 1}).status_code == 400
        r = c.post("/register/1", data={"customer_name": "Ade", "phone": "08031234567"}, follow_redirects=False)
        assert r.status_code == 303
        assert c.get("/admin", follow_redirects=False).status_code == 303
        assert c.post("/admin/login", data={"password": "bad"}).status_code == 401
        assert c.post("/admin/login", data={"password": "pw"}, follow_redirects=False).status_code == 303
        page = c.get("/admin")
        assert page.status_code == 200 and "Ade" in page.text
        assert c.post("/admin/orders/1/status", data={"status": "confirmed"}, follow_redirects=False).status_code == 303
        assert c.post("/admin/products/1/stock", follow_redirects=False).status_code == 303
        assert c.get("/admin/products").status_code == 200
