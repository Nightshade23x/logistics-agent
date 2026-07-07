from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.backend_service import process_json_file_request
from app.output_text_cleaner import clean_output_payload


BAD_STRINGS = [
    "Trader,and",
    "DAP,DDP",
    "20ftStandard",
    "beforebooking",
    "reliableestimate",
    "calculatinglanded",
    "transportdocument",
    "beforetreating",
    "reviewis",
]


def test_output_text_cleaner_recursively_cleans_strings():
    payload = {
        "a": "Trader,and DAP,DDP 20ftStandard beforebooking",
        "b": [
            "reliableestimate calculatinglanded",
            {"c": "transportdocument beforetreating reviewis"},
        ],
    }

    cleaned = clean_output_payload(payload)
    serialized = json.dumps(cleaned)

    for bad_string in BAD_STRINGS:
        assert bad_string not in serialized


def test_backend_payload_has_no_known_spacing_artifacts():
    payload = process_json_file_request(
        ROOT_DIR / "data" / "suppliers" / "sample_shopping_request.json"
    )

    serialized = json.dumps(payload)

    for bad_string in BAD_STRINGS:
        assert bad_string not in serialized


def main() -> None:
    test_output_text_cleaner_recursively_cleans_strings()
    test_backend_payload_has_no_known_spacing_artifacts()

    print("All output text cleaner tests passed.")


if __name__ == "__main__":
    main()
