"""Excel / CSV IO and interactive HTML report generation."""
from __future__ import annotations
import json
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


def export_html_report(result: AllocationResult, out_path: str) -> None:
    """Generate an interactive HTML report with chart + search."""
    result.assert_approved()
    log.info("خروجی HTML: %s", out_path)
    loads = result.load_per_mentor()
    moved = [
        {"name": f"{s.first} {s.last}".strip() or s.counter,
         "from": s.initial_supporter, "to": result.mentor_for_student(i)}
        for i, s in enumerate(result.students)
        if i not in result.stabilized
    ]
    data = json.dumps(
        {"loads": loads,
         "moved": moved,
         "stats": dict(_stats_list(result))},
        ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    Path(out_path).write_text(
        _HTML_TEMPLATE.replace("__DATA__", data), encoding="utf-8")
    log.info("گزارش HTML ذخیره شد: %s", out_path)


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<title>گزارش تخصیص</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  *{box-sizing:border-box}
  body{font-family:Tahoma,sans-serif;margin:24px;
       background:#1a1a2e;color:#e2e8f0}
  h1{color:#4cc9f0}h2{color:#94a3b8;font-size:14px}
  .card{background:#16213e;padding:16px;border-radius:12px;
        margin:16px 0;border:1px solid #2d3748}
  table{border-collapse:collapse;width:100%}
  th,td{border:1px solid #2d3748;padding:8px;text-align:right}
  th{background:#0f3460;color:#e2e8f0}
  tr:nth-child(even){background:#1e2a45}
  input{padding:8px;width:100%;margin:8px 0;
        background:#1e2a45;color:#e2e8f0;
        border:1px solid #2d3748;border-radius:6px}
  .badge{display:inline-block;padding:2px 10px;
         border-radius:12px;font-size:12px}
  .ok{background:#1b5e20;color:#a5d6a7}
  .warn{background:#e65100;color:#ffe0b2}
  .over{background:#b71c1c;color:#ffcdd2}
</style>
</head>
<body>
<h1>📊 گزارش تخصیص دانش‌آموزان</h1>
<div class="card">
  <h2>آمار کلی</h2>
  <div id="stats"></div>
</div>
<div class="card">
  <h2>نمودار توزیع</h2>
  <canvas id="chart" height="100"></canvas>
</div>
<div class="card">
  <h2>دانش‌آموزان جابه‌جا شده (<span id="mc"></span>)</h2>
  <input id="search" placeholder="جستجو در نام..."/>
  <table id="tbl">
    <thead><tr><th>نام</th><th>پشتیبان اولیه</th>
    <th>پشتیبان نهایی</th></tr></thead>
    <tbody></tbody>
  </table>
</div>
<script>
const D = __DATA__;
// stats
const stats = document.getElementById("stats");
Object.entries(D.stats).forEach(([k,v])=>{
  const bold=document.createElement("b");
  bold.textContent=k+": ";
  stats.append(bold,document.createTextNode(String(v)+"   "));
});
// chart
const cap = D.stats["ظرفیت محاسبه‌شده هر پشتیبان"] || 0;
const colors = Object.values(D.loads).map(v =>
  v > cap ? "#ef5350" : v === cap ? "#ffb74d" : "#4361ee");
new Chart(document.getElementById("chart"),{
  type:"bar",
  data:{labels:Object.keys(D.loads),
        datasets:[{label:"دانش‌آموز",
                   data:Object.values(D.loads),
                   backgroundColor:colors}]},
  options:{plugins:{legend:{display:false}},
           scales:{x:{ticks:{color:"#e2e8f0"},
                      grid:{color:"#2d3748"}},
                   y:{ticks:{color:"#e2e8f0"},
                      grid:{color:"#2d3748"}}}}
});
// table
document.getElementById("mc").textContent = D.moved.length;
const tb = document.querySelector("#tbl tbody");
function render(f){
  tb.innerHTML="";
  D.moved.filter(m=>!f||m.name.includes(f)).forEach(m=>{
    const row=document.createElement("tr");
    for(const value of [m.name,m.from,m.to]){
      const cell=document.createElement("td");
      cell.textContent=value;
      row.appendChild(cell);
    }
    tb.appendChild(row);
  });
}
render("");
document.getElementById("search").oninput=e=>render(e.target.value);
</script>
</body></html>"""
