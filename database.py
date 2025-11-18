import os
from datetime import datetime
from typing import Any, Dict, List
from pymongo import MongoClient

DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "appdb")

client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]


def create_document(collection_name: str, data: Dict[str, Any]) -> str:
    now = datetime.utcnow()
    data["created_at"] = now
    data["updated_at"] = now
    res = db[collection_name].insert_one(data)
    return str(res.inserted_id)


def get_documents(collection_name: str, filter_dict: Dict[str, Any] | None = None, limit: int | None = None) -> List[Dict[str, Any]]:
    cursor = db[collection_name].find(filter_dict or {})
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)
