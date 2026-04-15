"""
database.py
-----------
MongoDB persistence layer for loan application audit trails.
Uses pymongo for synchronous operations.
Gracefully degrades (with warnings) if MongoDB is unavailable.
"""

from typing import Optional
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION
from utils import logger


# ──────────────────────────────────────────────
# Connection Management
# ──────────────────────────────────────────────

_client: Optional[MongoClient] = None
_collection = None


def _get_collection():
    """Lazily initialise and return the MongoDB collection handle."""
    global _client, _collection

    if _collection is not None:
        return _collection

    try:
        _client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000,   # 3-second connection timeout
        )
        # Ping to verify connection is alive
        _client.admin.command("ping")
        db = _client[MONGO_DB]
        _collection = db[MONGO_COLLECTION]

        # Ensure indexes for efficient lookups
        _collection.create_index("application_id", unique=True)
        _collection.create_index("timestamp")

        logger.info("MongoDB connected: %s → %s.%s", MONGO_URI, MONGO_DB, MONGO_COLLECTION)

    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.warning(
            "MongoDB unavailable (%s). Audit records will NOT be persisted.", exc
        )
        _collection = None

    return _collection


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def save_audit_record(record: dict) -> bool:
    """
    Persist a full audit record to MongoDB.

    Args:
        record: Serialisable dict containing input, features, and output.

    Returns:
        True if saved successfully, False otherwise.
    """
    coll = _get_collection()
    if coll is None:
        logger.warning(
            "Skipping DB write for application_id=%s (no DB connection).",
            record.get("application_id", "UNKNOWN"),
        )
        return False

    try:
        result = coll.insert_one(record)
        logger.info(
            "Audit record saved. application_id=%s  _id=%s",
            record.get("application_id"),
            result.inserted_id,
        )
        return True
    except Exception as exc:
        logger.error("Failed to save audit record: %s", exc)
        return False


def fetch_by_application_id(application_id: str) -> Optional[dict]:
    """
    Retrieve a single audit record by application ID.

    Returns:
        The document dict (without Mongo's internal _id), or None if not found.
    """
    coll = _get_collection()
    if coll is None:
        return None

    try:
        doc = coll.find_one(
            {"application_id": application_id},
            {"_id": 0},  # Exclude internal Mongo _id
        )
        return doc
    except Exception as exc:
        logger.error("Fetch failed for application_id=%s: %s", application_id, exc)
        return None


def close_connection() -> None:
    """Close the MongoDB client connection."""
    global _client, _collection
    if _client:
        _client.close()
        _client = None
        _collection = None
        logger.info("MongoDB connection closed.")
