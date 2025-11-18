from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import os

from database import db, create_document, get_documents
from schemas import (
    CustomerCreate, CustomerOut,
    MenuImportPayload, MenuCategoryOut, MenuItemOut,
    OrderCreateItem, OrderCreate, OrderOut,
    BookingCreate, BookingOut,
    PaymentCreate, PaymentOut
)

app = FastAPI(title="Arman Specialty Coffee API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def oid(obj: Any) -> str:
    if isinstance(obj, ObjectId):
        return str(obj)
    return obj


def serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["id"] = oid(doc.pop("_id"))
    return doc


@app.get("/")
def root():
    return {"message": "Arman Specialty Coffee API running"}


@app.get("/test")
def test_db():
    try:
        collections = db.list_collection_names()
        return {
            "backend": "fastapi",
            "database": "mongodb",
            "database_url": os.getenv("DATABASE_URL", "(env not set)"),
            "database_name": os.getenv("DATABASE_NAME", "(env not set)"),
            "connection_status": "ok",
            "collections": collections,
        }
    except Exception as e:
        return {"backend": "fastapi", "database": "mongodb", "connection_status": f"error: {e}"}


# ============== MENU ==================
@app.get("/menu", response_model=List[MenuCategoryOut])
def get_menu():
    # Build categories with items
    categories = list(db["menucategory"].find({"disabled": {"$ne": True}}).sort("order", 1))
    cat_ids = [c["_id"] for c in categories]
    items = list(db["menuitem"].find({"category_id": {"$in": cat_ids}, "disabled": {"$ne": True}}))
    items_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        items_by_cat.setdefault(str(it.get("category_id")), []).append(serialize(it))
    result: List[Dict[str, Any]] = []
    for c in categories:
        result.append({
            "id": str(c["_id"]),
            "name": c.get("name"),
            "slug": c.get("slug"),
            "order": c.get("order", 0),
            "items": items_by_cat.get(str(c["_id"]), [])
        })
    return result


@app.post("/admin/menu/import")
def import_menu(payload: MenuImportPayload):
    # Clear existing
    db["menucategory"].delete_many({})
    db["menuitem"].delete_many({})

    # Insert categories and items
    for idx, cat in enumerate(payload.categories):
        cat_doc = {
            "name": cat.name,
            "slug": cat.slug or cat.name.lower().replace(" ", "-"),
            "order": cat.order if cat.order is not None else idx,
            "disabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        cat_id = db["menucategory"].insert_one(cat_doc).inserted_id
        for item in cat.items:
            db["menuitem"].insert_one({
                "category_id": cat_id,
                "name": item.name,
                "price": item.price,
                "image": item.image,
                "description": item.description,
                "options": item.options or {},
                "disabled": item.disabled or False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
    return {"status": "ok"}


# ============== AUTH / CUSTOMERS ==================
@app.post("/auth/send_otp")
def send_otp(phone: str = Body(..., embed=True)):
    # Demo OTP flow
    code = "1234"
    db["otp"].update_one({"phone": phone}, {"$set": {"phone": phone, "code": code, "created_at": datetime.utcnow()}}, upsert=True)
    return {"sent": True, "debug_code": code}


@app.post("/auth/verify_otp", response_model=CustomerOut)
def verify_otp(phone: str = Body(..., embed=True), code: str = Body(..., embed=True), name: Optional[str] = Body(None, embed=True)):
    rec = db["otp"].find_one({"phone": phone})
    if not rec or rec.get("code") != code:
        raise HTTPException(status_code=400, detail="Invalid code")

    existing = db["customer"].find_one({"phone": phone})
    if existing:
        db["otp"].delete_one({"phone": phone})
        return CustomerOut(id=str(existing["_id"]), name=existing.get("name"), phone=existing.get("phone"))

    if not name:
        raise HTTPException(status_code=400, detail="Name required for new customer")

    cust_id = create_document("customer", {"name": name, "phone": phone})
    db["otp"].delete_one({"phone": phone})
    cust = db["customer"].find_one({"_id": ObjectId(cust_id)})
    return CustomerOut(id=cust_id, name=cust.get("name"), phone=cust.get("phone"))


@app.get("/customers/{phone}", response_model=Optional[CustomerOut])
def get_customer(phone: str):
    cust = db["customer"].find_one({"phone": phone})
    if not cust:
        return None
    return CustomerOut(id=str(cust["_id"]), name=cust.get("name"), phone=cust.get("phone"))


# ============== ORDERS & PAYMENTS ==================
@app.post("/orders", response_model=OrderOut)
def create_order(order: OrderCreate):
    # Compute totals
    total = 0.0
    line_items = []
    for it in order.items:
        item = db["menuitem"].find_one({"_id": ObjectId(it.item_id)})
        if not item:
            raise HTTPException(status_code=404, detail=f"Item {it.item_id} not found")
        price = float(item.get("price", 0)) * it.qty
        total += price
        line_items.append({
            "item_id": item["_id"],
            "name": item.get("name"),
            "qty": it.qty,
            "price": float(item.get("price", 0)),
            "subtotal": price,
            "notes": it.notes,
            "selected_options": it.selected_options or {}
        })

    doc = {
        "customer_phone": order.customer_phone,
        "table_id": order.table_id,
        "type": order.type,
        "status": "pending",
        "items": line_items,
        "total": round(total, 2),
        "payment_status": "unpaid",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    oid_ = db["order"].insert_one(doc).inserted_id
    out = db["order"].find_one({"_id": oid_})
    return OrderOut(**serialize(out))


@app.get("/orders", response_model=List[OrderOut])
def list_orders(status: Optional[str] = None, phone: Optional[str] = None):
    q: Dict[str, Any] = {}
    if status:
        q["status"] = status
    if phone:
        q["customer_phone"] = phone
    orders = [serialize(o) for o in db["order"].find(q).sort("created_at", -1)]
    return [OrderOut(**o) for o in orders]


@app.post("/orders/{order_id}/status")
def update_order_status(order_id: str, status: str = Body(..., embed=True)):
    res = db["order"].update_one({"_id": ObjectId(order_id)}, {"$set": {"status": status, "updated_at": datetime.utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "ok"}


@app.post("/payments/create", response_model=PaymentOut)
def create_payment(p: PaymentCreate):
    order = db["order"].find_one({"_id": ObjectId(p.order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    amount = p.amount if p.amount is not None else order.get("total", 0)

    pay_doc = {
        "order_id": order["_id"],
        "amount": amount,
        "gateway": p.gateway or "demo",
        "status": "created",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    pid = db["payment"].insert_one(pay_doc).inserted_id
    payment_url = f"/payments/redirect?pid={pid}"
    out = db["payment"].find_one({"_id": pid})
    s = serialize(out)
    s["payment_url"] = payment_url
    return PaymentOut(**s)  # type: ignore


@app.post("/payments/webhook")
def payment_webhook(pid: str = Body(..., embed=True), status: str = Body("success", embed=True)):
    pay = db["payment"].find_one({"_id": ObjectId(pid)})
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")
    db["payment"].update_one({"_id": pay["_id"]}, {"$set": {"status": status, "updated_at": datetime.utcnow()}})
    if status == "success":
        db["order"].update_one({"_id": pay["order_id"]}, {"$set": {"payment_status": "paid", "status": "confirmed", "updated_at": datetime.utcnow()}})
    return {"ok": True}


# ============== BOOKINGS ==================
@app.post("/bookings", response_model=BookingOut)
def create_booking(b: BookingCreate):
    doc = {
        "name": b.name,
        "phone": b.phone,
        "party_size": b.party_size,
        "date": b.date,
        "time": b.time,
        "status": "confirmed",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    bid = db["booking"].insert_one(doc).inserted_id
    out = db["booking"].find_one({"_id": bid})
    return BookingOut(**serialize(out))


@app.get("/bookings", response_model=List[BookingOut])
def list_bookings():
    docs = [serialize(d) for d in db["booking"].find({}).sort("date", 1)]
    return [BookingOut(**d) for d in docs]


@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    res = db["booking"].update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": "cancelled", "updated_at": datetime.utcnow()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"status": "cancelled"}


# ============== TABLES ==================
@app.get("/tables/status")
def table_status():
    # Simple table map: derive from recent orders (demo)
    orders = list(db["order"].find({"table_id": {"$ne": None}}))
    status: Dict[str, str] = {}
    for o in orders:
        t = o.get("table_id")
        if not t:
            continue
        ps = o.get("payment_status", "unpaid")
        status[str(t)] = "occupied" if ps != "paid" else "available"
    return status
