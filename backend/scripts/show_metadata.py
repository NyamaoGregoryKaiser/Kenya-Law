#!/usr/bin/env python3
"""
Dev-only: print sample document metadata from kenyalaw_documents.
Run from backend dir: python3 scripts/show_metadata.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from document_index import document_indexer
from pprint import pprint

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    samples = document_indexer.get_sample_metadata(limit=n)
    print(f"Sample metadata ({len(samples)} docs):\n")
    pprint(samples)
