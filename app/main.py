import os
import re
import secrets
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, SQLModel, create_engine, select
from starlette.middleware.sessions import SessionMiddleware

from app.models import CATEGORIES, ORDER_STATUSES, Order, Product, Registration, Training
from app.seed import seed

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///esanfarmers.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
BUSINESS_WHATSAPP = os.getenv("BUSINESS_WHATSAPP", "2340000000000")
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "") == "1"

engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
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
    return templates.TemplateResponse(request, "index.html", {
        "products": products, "featured": featured, "trainings": trainings, "q": q, "category": category})


@app.get("/product/{pid}")
def product(request: Request, pid: int, s: Session = Depends(get_session)):
    p = s.get(Product, pid)
    if not p:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "product.html", {"p": p})


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
    return templates.TemplateResponse(request, "admin_dashboard.html", {
        "orders": orders, "regs": regs,
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
                use_for: str = Form(""), directions: str = Form(""), s: Session = Depends(get_session)):
    if category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")
    s.add(Product(name=name, category=category, price=price, pack=pack, active_ingredient=active_ingredient,
                  nafdac_no=nafdac_no, use_for=use_for, directions=directions))
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
        s.delete(p)
        s.commit()
    return RedirectResponse("/admin/products", status_code=303)
