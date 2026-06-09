"""Drag-and-drop file loading zone with browse fallback."""
from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFileDialog, QFrame, QLabel,
                               QPushButton, QVBoxLayout)

from app.utils.theme import ColorPalette as P


class FileDropZone(QFrame):
    """Drop area; emits :attr:`fileSelected` with the chosen path."""
    fileSelected = Signal(str)

    def __init__(self, title: str) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropzone")
        self.setStyleSheet(
            "QFrame#dropzone{"
            f"  border:2px dashed {P.ACCENT};"
            "  border-radius:12px;"
            f"  background:{P.BG_SURFACE};"
            "  min-height:120px;}"
            f"QFrame#dropzone:hover{{border-color:{P.ACCENT_LIGHT};}}")
        lay = QVBoxLayout(self)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info = QLabel("فایل را اینجا رها کنید")
        self.info.setObjectName("lbl_muted")
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("انتخاب فایل...")
        btn.setObjectName("btn_secondary")
        btn.clicked.connect(self._browse)
        for w in (lbl_title, self.info, btn):
            lay.addWidget(w)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل", "", "Excel/CSV (*.xlsx *.csv)")
        if path:
            self.fileSelected.emit(path)

    def dragEnterEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            self.setStyleSheet(
                "QFrame#dropzone{"
                f"  border:2px solid {P.SUCCESS_LIGHT};"
                "  border-radius:12px;"
                f"  background:{P.BG_INPUT};"
                "  min-height:120px;}")
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):  # noqa: N802
        self._reset_style()

    def dropEvent(self, e):  # noqa: N802
        self._reset_style()
        urls = e.mimeData().urls()
        if urls:
            self.fileSelected.emit(urls[0].toLocalFile())

    def _reset_style(self) -> None:
        self.setStyleSheet(
            "QFrame#dropzone{"
            f"  border:2px dashed {P.ACCENT};"
            "  border-radius:12px;"
            f"  background:{P.BG_SURFACE};"
            "  min-height:120px;}"
            f"QFrame#dropzone:hover{{border-color:{P.ACCENT_LIGHT};}}")

    def set_status(self, text: str) -> None:
        self.info.setText(text)
