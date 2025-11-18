from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# Collections:
# - user
# - menu_category
# - menu_item
# - order
# - booking
# - table

class User(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    name: str
    role: Literal["customer", "staff", "admin"] = "customer"
    is_active: bool = True

class MenuCategory(BaseModel):
    name: str
    slug: str
    is_active: bool = True
    sort: int = 0

class MenuItem(BaseModel):
    category_slug: str
    name: str
    description: Optional[str] = None
    price: float
    image: Optional[str] = None
    is_active: bool = True
    tags: List[str] = []

class CartItem(BaseModel):
    item_id: str
    name: str
    qty: int = 1
    price: float
    notes: Optional[str] = None

class Order(BaseModel):
    order_type: Literal["dine-in", "takeaway"]
    table_id: Optional[str] = None
    phone: Optional[str] = None
    items: List[CartItem]
    subtotal: float
    tax: float = 0
    total: float
    status: Literal["pending", "paid", "cancelled"] = "pending"
    payment_method: Optional[Literal["cash", "card", "online"]] = None

class Booking(BaseModel):
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    name: str
    phone: str
    party_size: int
    status: Literal["booked", "cancelled"] = "booked"

class Table(BaseModel):
    table_number: int
    qr_code: Optional[str] = None
    status: Literal["available", "occupied", "reserved"] = "available"
