"""Code Doctor — وضعیت فعلی باگ‌های شناخته‌شده را گزارش می‌دهد."""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "fair_algorithm": ROOT / "app" / "core" / "fair_algorithm.py",
    "mini_dashboard": ROOT / "app" / "ui" / "widgets" / "mini_dashboard.py",
    "step3_settings": ROOT / "app" / "ui" / "pages" / "step3_settings.py",
}

def check_fair_algorithm() -> list[str]:
    issues = []
    code = FILES["fair_algorithm"].read_text(encoding="utf-8")

    if 'getattr(m, \'capacity\'' not in code and 'getattr(m, "capacity"' not in code:
        issues.append("capacity بدون getattr — ممکن است AttributeError بدهد")

    if "if _mgr_abs_load(over_mgr) <= math.ceil" not in code:
        issues.append("بازبررسی threshold داخل حلقه over_m وجود ندارد (over-correction ممکن)")

    if "Rebalance Pass" not in code:
        issues.append("نسخه جدید ManagerBalancedStrategy اعمال نشده")

    return issues

def check_mini_dashboard() -> list[str]:
    issues = []
    code = FILES["mini_dashboard"].read_text(encoding="utf-8")

    if 'FairnessMode' not in code:
        issues.append("FairnessMode ایمپورت نشده — مقایسه enum با string ممکن است")

    if 'fairness_mode != FairnessMode.MANAGER_BALANCED' not in code:
        issues.append("مقایسه enum با string هنوز وجود دارد (rebalance box کار نمی‌کند)")

    return issues

def check_step3() -> list[str]:
    issues = []
    code = FILES["step3_settings"].read_text(encoding="utf-8")

    if "def sync_from_state" not in code:
        issues.append("متد sync_from_state پیاده‌سازی نشده")

    if "QTimer" not in code:
        issues.append("debounce برای capacity_spin وجود ندارد")

    return issues

def main():
    print("=== Code Doctor Report ===\n")

    for name, path in FILES.items():
        if not path.exists():
            print(f"[{name}] ❌ فایل پیدا نشد: {path}")
            continue

        if name == "fair_algorithm":
            issues = check_fair_algorithm()
        elif name == "mini_dashboard":
            issues = check_mini_dashboard()
        elif name == "step3_settings":
            issues = check_step3()
        else:
            issues = []

        if issues:
            print(f"[{name}] ⚠️ مشکلات:")
            for i in issues:
                print(f"  - {i}")
        else:
            print(f"[{name}] ✅ تمیز به نظر می‌رسد")

    print("\n=== پایان گزارش ===")

if __name__ == "__main__":
    main()