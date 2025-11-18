from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ---------- Menu ----------
class MenuItemIn(BaseModel):
    name: str
    price: float
    image: Optional[str] = None
    description: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    disabled: Optional[bool] = False

class MenuCategoryIn(BaseModel):
    name: str
    slug: Optional[str] = None
    order: Optional[int] = None
    items: List[MenuItemIn] = []

class MenuItemOut(BaseModel):
    id: str
    name: str
    price: float
    image: Optional[str] = None
    description: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

class MenuCategoryOut(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    order: int = 0
    items: List[MenuItemOut] = []

class MenuImportPayload(BaseModel):
    categories: List[MenuCategoryIn]

# ---------- Customers ----------
class CustomerCreate(BaseModel):
    name: str
    phone: str

class CustomerOut(BaseModel):
    id: str
    name: str
    phone: str

# ---------- Orders ----------
class OrderCreateItem(BaseModel):
    item_id: str
    qty: int = 1
    notes: Optional[str] = None
    selected_options: Optional[Dict[str, Any]] = None

class OrderCreate(BaseModel):
    customer_phone: Optional[str] = None
    table_id: Optional[str] = None
    type: str = Field(default="dine-in", description="dine-in or takeaway")
    items: List[OrderCreateItem]

class OrderOut(BaseModel):
    id: str
    customer_phone: Optional[str]
    table_id: Optional[str]
    type: str
    status: str
    items: List[Dict[str, Any]]
    total: float
    payment_status: str

# ---------- Bookings ----------
class BookingCreate(BaseModel):
    name: str
    phone: str
    party_size: int
    date: str
    time: str

class BookingOut(BaseModel):
    id: str
    name: str
    phone: str
    party_size: int
    date: str
    time: str
    status: str

# ---------- Payments ----------
class PaymentCreate(BaseModel):
    order_id: str
    gateway: Optional[str] = None
    amount: Optional[float] = None

class PaymentOut(BaseModel):
    id: str
    order_id: str
    amount: float
    gateway: str
    status: str
    payment_url: Optional[str] = None
