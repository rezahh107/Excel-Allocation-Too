"""Text normalisation and raw CSV/XLSX parsing."""
from __future__ import annotations
import csv
from typing import Any

from app.utils.logger import get_logger

log = get_logger("parser")


def normalize_text(s: Any) -> str:
    """Normalise Persian/Arabic text for robust matching.

    * Converts Arabic ي / ك to Persian ی / ک.
    * Converts final ة to ه.
    * Collapses whitespace.
    """
    if not isinstance(s, str):
        return "" if s is None else str(s)
    s = s.replace("ي", "ی").replace("ك", "ک")
    if s.endswith("ة"):
        s = s[:-1] + "ه"
    return " ".join(s.split()).strip()


def load_csv(filename: str, encoding: str = "utf-8-sig",
             delimiter: str = ";") -> list[dict[str, str]]:
    """Load a delimited text file with normalised keys and values."""
    rows: list[dict[str, str]] = []
    try:
        with open(filename, "r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                rows.append({normalize_text(k): normalize_text(v)
                             for k, v in row.items()})
        log.debug("بارگذاری CSV: %s (%d ردیف)", filename, len(rows))
    except Exception as exc:  # noqa: BLE001
        log.error("خطا در بارگذاری CSV %s: %s", filename, exc)
        raise
    return rows
