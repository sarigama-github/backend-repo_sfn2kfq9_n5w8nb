from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from database import create_document, get_documents, collection
from schemas import User, MenuCategory, MenuItem, Order, Booking, Table

app = FastAPI(title="Arman Speciality Coffee API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/test")
async def test():
    # verify db connection by listing collections
    cols = await _list_collections()
    return {"ok": True, "collections": cols}


async def _list_collections() -> List[str]:
    db = collection("dummy").database
    return db.list_collection_names()


# Auth: phone-first register/login (simple)
class PhonePayload(BaseModel):
    phone: str
    name: Optional[str] = None


@app.post("/auth/phone")
async def phone_login(payload: PhonePayload):
    phone = payload.phone
    users = get_documents("user", {"phone": phone}, limit=1)
    if users:
        return {"status": "existing", "user": users[0]}
    if not payload.name:
        return {"status": "new", "message": "name_required"}
    user = User(phone=payload.phone, name=payload.name)
    _id = create_document("user", user.model_dump())
    return {"status": "created", "user_id": _id}


# Menu endpoints (ingestion from provided JSON)
class MenuIngest(BaseModel):
    categories: List[MenuCategory]
    items: List[MenuItem]


@app.post("/menu/ingest")
async def ingest_menu(data: MenuIngest):
    # clear and insert
    db = collection("menu_item").database
    db["menu_category"].delete_many({})
    db["menu_item"].delete_many({})
    for c in data.categories:
        create_document("menu_category", c.model_dump())
    for i in data.items:
        create_document("menu_item", i.model_dump())
    return {"ok": True}


@app.get("/menu")
async def get_menu():
    cats = get_documents("menu_category", {"is_active": True}, limit=100)
    items = get_documents("menu_item", {"is_active": True}, limit=1000)
    return {"categories": cats, "items": items}


# Orders
@app.post("/orders")
async def create_order(order: Order):
    _id = create_document("order", order.model_dump())
    return {"order_id": _id}


@app.get("/orders")
async def list_orders(status: Optional[str] = None):
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    orders = get_documents("order", q, limit=200)
    return {"orders": orders}


# Bookings
@app.post("/bookings")
async def create_booking(booking: Booking):
    _id = create_document("booking", booking.model_dump())
    return {"booking_id": _id}


@app.get("/bookings")
async def list_bookings(date: Optional[str] = None):
    q: Dict[str, Any] = {}
    if date:
        q["date"] = date
    bookings = get_documents("booking", q, limit=200)
    return {"bookings": bookings}


# Tables
@app.get("/tables")
async def list_tables():
    tables = get_documents("table", {}, limit=200)
    return {"tables": tables}


@app.post("/tables")
async def add_table(table: Table):
    _id = create_document("table", table.model_dump())
    return {"table_id": _id}


# Payment stubs (simulate until gateway keys added)
class PaymentInit(BaseModel):
    phone: str
    amount: float


@app.post("/payments/init")
async def payment_init(p: PaymentInit):
    # In real integration, create Razorpay order here and return order_id & key
    return {"payment_url": "/payment/success?amount=" + str(p.amount), "amount": p.amount}


@app.post("/payments/webhook")
async def payment_webhook(request: Request):
    data = await request.json()
    # Verify signature in real integration
    return {"ok": True, "received": data}
