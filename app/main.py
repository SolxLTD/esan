import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy import inspect, text
from starlette.middleware.sessions import SessionMiddleware

import cloudinary
from cloudinary import uploader as cloudinary_uploader

from app.models import CATEGORIES, ORDER_STATUSES, Member, Order, Product, ProductPhoto, Registration, Training
from app.seed import seed

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///esanfarmers.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
BUSINESS_WHATSAPP = os.getenv("BUSINESS_WHATSAPP", "2340000000000")
TRAINING_YOUTUBE_URL = os.getenv(
    "TRAINING_YOUTUBE_URL",
    "https://www.youtube.com/results?search_query=Esan+Farmers+agriculture+training",
)
PRODUCT_PHOTO_DIR = Path(os.getenv("PRODUCT_PHOTO_DIR", "app/static/products"))
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "").strip()
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "") == "1"

engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    if "public_id" not in {column["name"] for column in inspect(engine).get_columns("productphoto")}:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE productphoto ADD COLUMN public_id VARCHAR NOT NULL DEFAULT ''"
            ))
    with Session(engine) as s:
        if not s.exec(select(Product)).first():
            seed(s)
    yield


app = FastAPI(title="Esan Farmers", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax",
                   https_only=HTTPS_ONLY, max_age=60 * 60 * 8)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["naira"] = lambda v: f"₦{v:,.0f}"
templates.env.globals["CATEGORIES"] = CATEGORIES
templates.env.globals["ORDER_STATUSES"] = ORDER_STATUSES
templates.env.globals["TRAINING_YOUTUBE_URL"] = TRAINING_YOUTUBE_URL


def get_session():
    with Session(engine) as s:
        yield s


def wa(msg: str) -> str:
    return f"https://wa.me/{BUSINESS_WHATSAPP}?text={quote(msg)}"


templates.env.globals["wa"] = wa


def clean_phone(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    if d.startswith("0") and len(d) == 11:
        d = "234" + d[1:]
    if not 10 <= len(d) <= 15:
        raise HTTPException(400, "Enter a valid phone number")
    return d


def require_admin(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(303, headers={"Location": "/admin/login"})


@app.get("/health")
def health(s: Session = Depends(get_session)):
    s.exec(select(Product).limit(1)).first()
    return JSONResponse({"status": "ok"})


# ---------- public ----------
@app.get("/")
def home(request: Request, q: str = "", category: str = "", s: Session = Depends(get_session)):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%") | Product.use_for.ilike(f"%{q}%")
                          | Product.active_ingredient.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Product.category == category)
    products = s.exec(stmt).all()
    featured = s.exec(select(Product).where(Product.featured == True).limit(4)).all()  # noqa: E712
    trainings = s.exec(select(Training).limit(3)).all()
    photo_by_product = {}
    for photo in s.exec(select(ProductPhoto)).all():
        photo_by_product.setdefault(photo.product_id, photo.image_path)
    return templates.TemplateResponse(request, "index.html", {
        "products": products, "featured": featured, "trainings": trainings, "q": q, "category": category,
        "photo_by_product": photo_by_product})


@app.get("/product/{pid}")
def product(request: Request, pid: int, s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if not p:
        raise HTTPException(404)
    photos = s.exec(select(ProductPhoto).where(ProductPhoto.product_id == pid).order_by(ProductPhoto.id)).all()
    return templates.TemplateResponse(request, "product.html", {"p": p, "photos": photos})


@app.post("/order/{pid}")
def place_order(pid: int, customer_name: str = Form(..., max_length=80), phone: str = Form(...),
                qty: int = Form(1, ge=1, le=1000), note: str = Form("", max_length=300),
                s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if not p or not p.in_stock:
        raise HTTPException(404, "Product not available")
    o = Order(product_id=p.id, product_name=p.name, qty=qty, customer_name=customer_name.strip(),
              phone=clean_phone(phone), note=note.strip())
    s.add(o)
    s.commit()
    s.refresh(o)
    msg = (f"Hello Esan Farmers, order #{o.id}: {qty} x {p.name} ({p.pack}). "
           f"Name: {o.customer_name}. Phone: {o.phone}." + (f" Note: {o.note}" if o.note else ""))
    return RedirectResponse(wa(msg), status_code=303)


@app.get("/training")
def training(request: Request, s: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "training.html", {"items": s.exec(select(Training)).all()})


@app.get("/training/field-guide")
def field_guide(request: Request):
    return templates.TemplateResponse(request, "field_guide.html")


@app.get("/register")
def member_registration(request: Request, submitted: bool = False):
    return templates.TemplateResponse(request, "register.html", {"submitted": submitted})


@app.post("/register")
def register_member(
    full_name: str = Form(..., max_length=80),
    phone: str = Form(...),
    email: str = Form("", max_length=254),
    interest: str = Form("", max_length=80),
    s: Session = Depends(get_session),
):
    member = Member(
        full_name=full_name.strip(),
        phone=clean_phone(phone),
        email=email.strip(),
        interest=interest.strip(),
    )
    if not member.full_name:
        raise HTTPException(400, "Enter your name")
    s.add(member)
    s.commit()
    return RedirectResponse("/register?submitted=true", status_code=303)


@app.post("/register/{tid}")
def register(tid: int, customer_name: str = Form(..., max_length=80), phone: str = Form(...),
             s: Session = Depends(get_session)):
    t = s.get(Training, tid)
    if not t:
        raise HTTPException(404)
    r = Registration(training_id=t.id, training_title=t.title, customer_name=customer_name.strip(),
                     phone=clean_phone(phone))
    s.add(r)
    s.commit()
    s.refresh(r)
    msg = f"Hello Esan Farmers, registration #{r.id} for: {t.title}. Name: {r.customer_name}. Phone: {r.phone}."
    return RedirectResponse(wa(msg), status_code=303)


# ---------- admin ----------
@app.get("/admin/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {"error": ""})


@app.post("/admin/login")
def login(request: Request, password: str = Form(...)):
    if not ADMIN_PASSWORD:
        raise HTTPException(503, "Admin is disabled: set ADMIN_PASSWORD")
    if not secrets.compare_digest(password, ADMIN_PASSWORD):
        return templates.TemplateResponse(request, "admin_login.html", {"error": "Wrong password"}, status_code=401)
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/admin", dependencies=[Depends(require_admin)])
def dashboard(request: Request, s: Session = Depends(get_session)):
    orders = s.exec(select(Order).order_by(Order.id.desc()).limit(50)).all()
    regs = s.exec(select(Registration).order_by(Registration.id.desc()).limit(50)).all()
    members = s.exec(select(Member).order_by(Member.id.desc()).limit(50)).all()
    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "orders": orders, "regs": regs, "members": members,
        "new_orders": sum(o.status == "new" for o in orders), "new_regs": sum(r.status == "new" for r in regs)})


@app.post("/admin/orders/{oid}/status", dependencies=[Depends(require_admin)])
def order_status(oid: int, status: str = Form(...), s: Session = Depends(get_session)):
    o = s.get(Order, oid)
    if not o or status not in ORDER_STATUSES:
        raise HTTPException(400)
    o.status = status
    s.add(o)
    s.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/registrations/{rid}/status", dependencies=[Depends(require_admin)])
def reg_status(rid: int, status: str = Form(...), s: Session = Depends(get_session)):
    r = s.get(Registration, rid)
    if not r or status not in ORDER_STATUSES:
        raise HTTPException(400)
    r.status = status
    s.add(r)
    s.commit()
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin/products", dependencies=[Depends(require_admin)])
def admin_products(request: Request, s: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "admin_products.html", {"products": s.exec(select(Product)).all()})


@app.post("/admin/products", dependencies=[Depends(require_admin)])
def add_product(name: str = Form(...), category: str = Form(...), price: int = Form(..., ge=0),
                pack: str = Form(...), active_ingredient: str = Form(""), nafdac_no: str = Form(""),
                use_for: str = Form(""), directions: str = Form(""), description: str = Form(..., min_length=10),
                s: Session = Depends(get_session)):
    if category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    s.add(Product(name=name, category=category, price=price, pack=pack, active_ingredient=active_ingredient,
                  nafdac_no=nafdac_no, use_for=use_for, directions=directions, description=description.strip()))
    s.commit()
    return RedirectResponse("/admin/products", status_code=303)


def image_extension(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    raise HTTPException(400, "Upload PNG, JPEG or WebP product photos")


def remove_product_photo(photo: ProductPhoto) -> None:
    if photo.public_id:
        result = cloudinary_uploader.destroy(photo.public_id, resource_type="image")
        if result.get("result") not in {"ok", "not found"}:
            raise HTTPException(502, "Cloudinary could not remove an old product photo")
    elif photo.image_path.startswith("/static/"):
        local_path = Path("app/static") / photo.image_path.removeprefix("/static/")
        if local_path.is_file():
            local_path.unlink()


@app.post("/admin/products/{pid}/photos", dependencies=[Depends(require_admin)])
def upload_product_photos(
    pid: int,
    photos: list[UploadFile] = File(...),
    s: Session = Depends(get_session),
):
    product = s.get(Product, pid)
    if not product:
        raise HTTPException(404)
    if not 3 <= len(photos) <= 5:
        raise HTTPException(400, "Upload between 3 and 5 photos for each product")

    if CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
    else:
        PRODUCT_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    photo_records = []
    for photo in photos:
        content = photo.file.read(5 * 1024 * 1024 + 1)
        if not content or len(content) > 5 * 1024 * 1024:
            raise HTTPException(400, "Each photo must be between 1 byte and 5 MB")
        extension = image_extension(content)
        filename = f"{secrets.token_hex(16)}{extension}"
        if CLOUDINARY_URL:
            upload = cloudinary_uploader.upload(
                content,
                folder="esan-farmers/products",
                public_id=filename.rsplit(".", 1)[0],
                resource_type="image",
            )
            image_path = upload.get("secure_url")
            public_id = upload.get("public_id")
            if not image_path or not public_id:
                raise HTTPException(502, "Cloudinary did not return the uploaded photo details")
        else:
            destination = PRODUCT_PHOTO_DIR / filename
            destination.write_bytes(content)
            image_path = f"/static/products/{filename}"
            public_id = ""
        photo_records.append(ProductPhoto(
            product_id=pid,
            image_path=image_path,
            alt_text=f"{product.name} product photo",
            public_id=public_id,
        ))

    old_photos = s.exec(select(ProductPhoto).where(ProductPhoto.product_id == pid)).all()
    for old_photo in old_photos:
        remove_product_photo(old_photo)
    for old_photo in old_photos:
        s.delete(old_photo)
    s.add_all(photo_records)
    s.commit()
    return RedirectResponse("/admin/products", status_code=303)


@app.post("/admin/products/{pid}/price", dependencies=[Depends(require_admin)])
def set_price(pid: int, price: int = Form(..., ge=0), s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if not p:
        raise HTTPException(404)
    p.price = price
    s.add(p)
    s.commit()
    return RedirectResponse("/admin/products", status_code=303)


@app.post("/admin/products/{pid}/stock", dependencies=[Depends(require_admin)])
def toggle_stock(pid: int, s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if not p:
        raise HTTPException(404)
    p.in_stock = not p.in_stock
    s.add(p)
    s.commit()
    return RedirectResponse("/admin/products", status_code=303)


@app.post("/admin/products/{pid}/delete", dependencies=[Depends(require_admin)])
def delete_product(pid: int, s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if p:
        photos = s.exec(select(ProductPhoto).where(ProductPhoto.product_id == pid)).all()
        for photo in photos:
            remove_product_photo(photo)
        for photo in photos:
            s.delete(photo)
        s.delete(p)
        s.commit()
    return RedirectResponse("/admin/products", status_code=303)
