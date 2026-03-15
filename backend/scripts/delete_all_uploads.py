#!/usr/bin/env python3
"""
Delete all uploaded files and their data from vector stores (Qdrant).
Use this to start fresh before re-uploading. Run from backend dir:

  cd ~/demos/Kenya-Law/backend
  source venv/bin/activate
  python3 scripts/delete_all_uploads.py
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env so DATABASE_URL, QDRANT_* etc. are set
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except Exception:
    pass

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
INDEX_STATUS_PATH = os.path.join(UPLOAD_DIR, ".index_status.json")


def main():
    if not os.path.isdir(UPLOAD_DIR):
        print(f"Upload directory not found: {UPLOAD_DIR}")
        sys.exit(1)

    from rag_system import rag_system
    from document_index import document_indexer

    names = [
        n for n in os.listdir(UPLOAD_DIR)
        if n != ".index_status.json" and os.path.isfile(os.path.join(UPLOAD_DIR, n))
    ]

    if not names:
        print("No files to delete in uploads.")
        # Still clear index status
        try:
            with open(INDEX_STATUS_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
            print("Cleared .index_status.json")
        except Exception as e:
            print(f"Could not clear index status: {e}")
        return

    print(f"Found {len(names)} file(s). Deleting from vector stores and disk...")
    deleted = 0
    errors = 0
    for name in names:
        path = os.path.join(UPLOAD_DIR, name)
        try:
            rag_system.delete_document(name)
        except Exception as e:
            print(f"  [warn] Vector (chunks) for {name}: {e}")
            errors += 1
        try:
            document_indexer.delete_by_filename(name)
        except Exception as e:
            print(f"  [warn] Document index for {name}: {e}")
            errors += 1
        try:
            os.remove(path)
            deleted += 1
            print(f"  Deleted: {name}")
        except Exception as e:
            print(f"  [error] File {name}: {e}")
            errors += 1

    try:
        with open(INDEX_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print("Cleared .index_status.json")
    except Exception as e:
        print(f"Could not clear index status: {e}")
        errors += 1

    print(f"Done. Removed {deleted} file(s). Errors: {errors}")


if __name__ == "__main__":
    main()
