from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "armancoffee")

_client: Optional[MongoClient] = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(DATABASE_URL)
        _db = _client[DATABASE_NAME]
    return _db


def collection(name: str) -> Collection:
    return get_db()[name]


def create_document(collection_name: str, data: Dict[str, Any]) -> str:
    col = collection(collection_name)
    now = datetime.utcnow()
    data = {
        **data,
        "created_at": now,
        "updated_at": now,
    }
    res = col.insert_one(data)
    return str(res.inserted_id)


def get_documents(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
    col = collection(collection_name)
    cursor = col.find(filter_dict or {}).limit(limit)
    items: List[Dict[str, Any]] = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])  # stringify ObjectId
        items.append(doc)
    return items
