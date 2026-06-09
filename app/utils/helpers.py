"""Generic helpers."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path


def open_in_explorer(path: str) -> None:
    """Open the folder containing *path* in the OS file explorer."""
    folder = str(Path(path).resolve().parent)
    if sys.platform.startswith("win"):
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", folder], check=False)
    else:
        subprocess.run(["xdg-open", folder], check=False)
