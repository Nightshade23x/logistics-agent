from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_status import build_backend_status


def main() -> None:
    status = build_backend_status()
    print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    main()
