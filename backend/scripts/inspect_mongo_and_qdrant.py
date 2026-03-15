#!/usr/bin/env python3
"""
Inspect MongoDB (documents, document_processing) and Qdrant (KL_LOOKUP) schema.
Run from repo root or backend/ with MONGODB_URI and optionally QDRANT_* set.

  cd backend && python scripts/inspect_mongo_and_qdrant.py

Output: collection names, sample documents, and field lists so we can
integrate KL_LOOKUP + MongoDB for chat references.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except Exception:
    pass


def _json_safe(obj):
    """Convert MongoDB types to JSON-serializable (e.g. ObjectId, datetime)."""
    return json.loads(json.dumps(obj, default=str))


def inspect_mongo():
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print("MONGODB_URI not set. Set it to e.g. mongodb://localhost:27017 or mongodb://user:pass@host:27017/dbname")
        return
    try:
        from pymongo import MongoClient
    except ImportError:
        print("pymongo not installed. Run: pip install pymongo")
        return
    print("=" * 60)
    print("MongoDB")
    print("=" * 60)
    client = MongoClient(uri)
    # Database name from URI path (e.g. mongodb://host:27017/kenyalaw -> kenyalaw)
    try:
        from urllib.parse import urlparse
        path = (urlparse(uri).path or "").strip("/")
        db_name = path or "kenyalaw"
    except Exception:
        db_name = "kenyalaw"
    db = client[db_name]
    print(f"Database: {db_name}")
    colls = db.list_collection_names()
    print(f"Collections: {colls}")
    print()
    for coll_name in ("documents", "document_processing"):
        if coll_name not in colls:
            print(f"[{coll_name}] (collection not found)")
            print()
            continue
        coll = db[coll_name]
        doc = coll.find_one()
        if not doc:
            print(f"[{coll_name}] (empty)")
            print()
            continue
        doc_safe = _json_safe(doc)
        print(f"[{coll_name}] fields: {list(doc_safe.keys())}")
        print(f"[{coll_name}] sample (one doc):")
        print(json.dumps(doc_safe, indent=2, default=str))
        print()
    client.close()


def inspect_qdrant():
    host = os.getenv("QDRANT_HOST", "127.0.0.1")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    lookup = os.getenv("QDRANT_KL_LOOKUP_COLLECTION", "KL_LOOKUP")
    print("=" * 60)
    print("Qdrant")
    print("=" * 60)
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        print("qdrant_client not installed.")
        return
    try:
        client = QdrantClient(host=host, port=port)
        colls = client.get_collections().collections
        names = [c.name for c in colls]
        print(f"Collections: {names}")
        if lookup in names:
            try:
                info = client.get_collection(lookup)
                vc = getattr(info, "vectors_count", None)
                pc = getattr(info, "points_count", None)
                print(f"\n[{lookup}] vectors_count={vc} points_count={pc}")
            except Exception as e:
                print(f"\n[{lookup}] (info: {e})")
            # One sample point (payload only, no vector)
            try:
                result, _ = client.scroll(collection_name=lookup, limit=1, with_payload=True, with_vectors=False)
                if result:
                    p = result[0].payload or {}
                    print(f"[{lookup}] sample payload keys: {list(p.keys())}")
                    print(f"[{lookup}] sample payload: {json.dumps(_json_safe(p), indent=2, default=str)}")
            except Exception as e:
                print(f"[{lookup}] scroll error: {e}")
        else:
            print(f"\n[{lookup}] collection not found")
        print()
    except Exception as e:
        print(f"Qdrant error: {e}")
        print()


if __name__ == "__main__":
    inspect_mongo()
    inspect_qdrant()
    print("Done. Use this output to wire KL_LOOKUP + MongoDB for chat references.")
