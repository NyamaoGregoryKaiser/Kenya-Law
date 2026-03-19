"""
MongoDB helpers for KL database: documents + document_processing.
Used to resolve document_name and status for chat references when using KL_LOOKUP (Qdrant).
"""
import os
import re
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("mongo_documents")

_client = None
_db_name = "KL"

def _get_client():
    global _client
    if _client is not None:
        return _client
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        return None
    try:
        from pymongo import MongoClient
        _client = MongoClient(uri)
        # Database name from URI path or default KL
        try:
            from urllib.parse import urlparse
            path = (urlparse(uri).path or "").strip("/")
            global _db_name
            _db_name = path or "KL"
        except Exception:
            pass
        return _client
    except Exception as e:
        logger.warning("MongoDB client init failed: %s", e)
        return None


def get_document_info(document_id: str) -> Optional[Dict[str, Any]]:
    """
    Get document details and processing status by document_id (UUID).
    Returns dict with document_name, document_path, status, processed, processing_status, etc.
    """
    client = _get_client()
    if not client:
        return None
    try:
        db = client[_db_name]
        doc = db["documents"].find_one({"document_id": document_id})
        if not doc:
            return None
        proc = db["document_processing"].find_one(
            {"document_id": document_id},
            sort=[("event_time", -1)]
        )
        out = {
            "document_id": document_id,
            "document_name": doc.get("document_name") or "",
            "document_path": doc.get("document_path") or "",
            "status": doc.get("status") or "",
            "processed": doc.get("processed", False),
        }
        if proc:
            out["processing_status"] = proc.get("status") or ""
            out["processing_processed"] = proc.get("processed", False)
        return out
    except Exception as e:
        logger.warning("get_document_info(%s) failed: %s", document_id, e)
        return None


def get_documents_info(document_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Resolve multiple document_ids; returns dict document_id -> info."""
    result = {}
    for did in document_ids:
        if did and did not in result:
            info = get_document_info(did)
            if info:
                result[did] = info
    return result


def parse_document_id_from_kl_lookup_text(text: str) -> Optional[str]:
    """
    Extract document_id (collection id) from KL_LOOKUP payload text.

    Boss spec: the first line is `COLLECTION-ID : <collection-id>`.
    We split the first line on ':' and take the second element.

    We also accept older variants like `CollectionID : <id>`.
    """
    if not text:
        return None
    first_line = (text.splitlines()[0] if text else "").strip()
    if first_line:
        parts = first_line.split(":", 1)
        if len(parts) == 2:
            key = parts[0].strip().lower().replace("_", "-")
            if key in ("collection-id", "collectionid"):
                val = parts[1].strip()
                return val or None
    # Fallback: scan anywhere in text for collection id markers
    m = re.search(r"(collection[\s\-_]*id)\s*:\s*([a-f0-9_]+)", text, re.IGNORECASE)
    return (m.group(2).strip() if m else None)
