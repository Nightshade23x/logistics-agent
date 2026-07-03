"""Shared helpers for repository classes that load JSON reference data."""

import json
from pathlib import Path
from typing import Any

# The data/ folder lives alongside repositories/, services/, schemas/, etc.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json_data(filename: str) -> Any:
    """Load and parse a JSON file from the package's data/ directory.

    Args:
        filename: The filename (e.g. "country_risk_index.json") within
            the data/ folder.

    Returns:
        The parsed JSON content (dict or list, depending on the file).

    Raises:
        FileNotFoundError: If the data file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    file_path = _DATA_DIR / filename
    with open(file_path, "r", encoding="utf-8") as data_file:
        return json.load(data_file)
