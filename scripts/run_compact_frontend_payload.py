from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import (
    process_document_files_request,
    process_json_file_request,
    process_text_request,
)
from app.compact_frontend_payload import build_compact_frontend_payload


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "Usage:\n"
            "  python scripts/run_compact_frontend_payload.py json <path>\n"
            "  python scripts/run_compact_frontend_payload.py text <request text>\n"
            "  python scripts/run_compact_frontend_payload.py docs <file1> <file2> ..."
        )

    request_type = sys.argv[1].lower()

    if request_type == "json":
        full_payload = process_json_file_request(Path(sys.argv[2]))

    elif request_type == "text":
        full_payload = process_text_request(" ".join(sys.argv[2:]))

    elif request_type in {"docs", "documents"}:
        full_payload = process_document_files_request(
            [Path(path) for path in sys.argv[2:]]
        )

    else:
        raise SystemExit(f"Unsupported request type: {request_type}")

    compact_payload = build_compact_frontend_payload(full_payload)

    print(json.dumps(compact_payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
