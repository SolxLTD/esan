from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

CATEGORIES = ["Herbicides", "Insecticides", "Fungicides", "Fertilizers", "Sprayers & Safety Gear"]
ORDER_STATUSES = ["new", "confirmed", "delivered", "cancelled"]


class Product(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    category: str
    price: int  # naira
    pack: str
    active_ingredient: str = ""
    nafdac_no: str = ""
    use_for: str = ""
    directions: str = ""
    description: str = ""
    featured: bool = False
    in_stock: bool = True


class ProductPhoto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: int = Field(index=True)
    image_path: str
    alt_text: str
    public_id: str = ""


class Training(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    duration: str
    price: int
    next_date: str = ""
    location: str = "Esan"


class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: int
    product_name: str
    qty: int = 1
    customer_name: str
    phone: str
    note: str = ""
    status: str = "new"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Registration(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    training_id: int
    training_title: str
    customer_name: str
    phone: str
    status: str = "new"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Member(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    phone: str
    email: str = ""
    interest: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
