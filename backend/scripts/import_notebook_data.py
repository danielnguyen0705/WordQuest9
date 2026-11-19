#!/usr/bin/env python3
"""
CLI Data Ingestion Pipeline for WordQuest 9.
Scans data/vocab/unit_X_vocab.json & data/questions/unit_X_questions.json,
validates against JSON Schemas, and UPSERTs into PostgreSQL (or configured DB).
"""

import argparse
import json
import sys
from pathlib import Path

# Add shared package to path when invoked directly
SHARED_DIR = Path(__file__).resolve().parents[1] / "shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Tiếng Anh 9 Notebook JSON data into WordQuest 9 DB.")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to data directory containing vocab/ and questions/")
    parser.add_argument("--unit", type=int, default=None, help="Only import a specific Unit (1-12)")
    parser.add_argument("--dry-run", action="store_true", help="Validate schemas without writing to DB")
    args = parser.parse_args()

    if not args.dry_run:
        init_db()

    db = SessionLocal()
    try:
        result = ingest_notebook_data(
            db=db,
            data_dir=args.data_dir,
            unit_filter=args.unit,
            dry_run=args.dry_run,
        )
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        if result.errors:
            return 1
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
