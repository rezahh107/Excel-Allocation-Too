"""Excel / CSV input and approved Excel allocation export."""
from __future__ import annotations
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.core.models import AllocationResult
from app.core.parser import load_csv, normalize_text
from app.utils.logger import get_logger

log = get_logger("excel_service")

HEADERS = [
    "شمارنده", "نام", "نام خانوادگی", "نام گروه", "مدیر",
    "پشتیبان اولیه", "پشتیبان نهایی", "مدیر پشتیبان نهایی",
]


def load_table(path: str) -> tuple[list[str], list[dict[str, str]]]:
    """Load a CSV or XLSX file.

    Returns:
        Tuple of ``(headers, rows)``.
    """
    p = Path(path)
    log.info("بارگذاری فایل: %s", path)
    if p.suffix.lower() == ".csv":
        rows = load_csv(path)
        return (list(rows[0].keys()) if rows else []), rows
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    try:
        raw = next(it)
    except StopIteration:
        return [], []
    headers = [normalize_text(h) for h in raw]
    rows: list[dict[str, str]] = []
    for r in it:
        rows.append({headers[i]: normalize_text(r[i] if i < len(r) else "")
                     for i in range(len(headers))})
    log.info("بارگذاری کامل: %d ردیف", len(rows))
    return headers, rows


def export_excel(result: AllocationResult,
                 mentor_manager: dict[str, str],
                 out_path: str) -> None:
    """Write the final assignment workbook (data + statistics sheets)."""
    result.assert_approved()
    canonical = {mentor.name: mentor.manager for mentor in result.mentors}
    if mentor_manager != canonical:
        raise ValueError("نگاشت مدیران خروجی با نتیجهٔ تأییدشده مغایرت دارد.")
    log.info("خروجی Excel: %s", out_path)
    wb = Workbook()
    ws = wb.active
    ws.title = "جدول نهایی دانش‌آموزان"
    ws.sheet_view.rightToLeft = True
    ws.append(HEADERS)
    for i, s in enumerate(result.students):
        final_mentor = result.mentor_for_student(i)
        ws.append([
            s.counter, s.first, s.last, s.group, s.manager,
            s.initial_supporter, final_mentor,
            mentor_manager.get(final_mentor, ""),
        ])
        # Spreadsheet-looking identifiers and text must never become formulas.
        for cell in ws[ws.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    ws2 = wb.create_sheet("گزارش آماری")
    ws2.sheet_view.rightToLeft = True
    ws2.append(["عنوان", "مقدار"])
    for title, value in _stats_list(result):
        ws2.append([title, value])
    wb.save(out_path)
    log.info("فایل ذخیره شد: %s", out_path)


def _stats_list(result: AllocationResult) -> list[tuple[str, int | float]]:
    loads = result.load_per_mentor()
    vals  = list(loads.values())
    avg   = round(sum(vals) / max(1, len(vals)), 2)
    return [
        ("تعداد کل دانش‌آموزان",           result.total_students),
        ("تعداد کل پشتیبان‌ها",             result.total_mentors),
        ("ظرفیت محاسبه‌شده هر پشتیبان",    result.capacity),
        ("حداقل تعداد دانش‌آموز",           min(vals) if vals else 0),
        ("حداکثر تعداد دانش‌آموز",          max(vals) if vals else 0),
        ("میانگین دانش‌آموز",               avg),
        ("تعداد تثبیت‌شده",                 len(result.stabilized)),
        ("تعداد جابه‌جا شده",               result.num_moved),
    ]

