from datetime import datetime
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
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Registration(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    training_id: int
    training_title: str
    customer_name: str
    phone: str
    status: str = "new"
    created_at: datetime = Field(default_factory=datetime.utcnow)
