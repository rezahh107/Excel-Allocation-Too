"""Non-modal simulation detail dialog (Step 3)."""
from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from app.core.models import FairnessMode, Mentor, Student
from app.services.simulation_service import (imbalance_report,
                                              original_loads, simulate)
from app.utils.rtl_utils import apply_rtl
from app.utils.theme import ColorPalette as P


class SimulationDialog(QDialog):
    """Show original load vs. final load vs. capacity per mentor."""

    def __init__(self, students: list[Student], mentors: list[Mentor],
                 mode: FairnessMode, parent=None) -> None:
        super().__init__(parent)
        apply_rtl(self)
        self.setWindowTitle("شبیه‌سازی توزیع")
        self.setModal(False)
        self.resize(580, 500)
        self._students = students
        self._mentors  = mentors
        self._mode     = mode

        lay = QVBoxLayout(self)
        self.summary = QLabel("")
        self.summary.setObjectName("lbl_muted")
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["نام پشتیبان", "بار اولیه", "بار نهایی", "ظرفیت"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        lay.addWidget(self.table)

        run_btn = QPushButton("اجرای شبیه‌سازی")
        run_btn.setObjectName("btn_primary")
        run_btn.clicked.connect(self.run_simulation)
        lay.addWidget(run_btn)
        self.run_simulation()

    def run_simulation(self) -> None:
        """Compute and display the simulation result."""
        result = simulate(self._students, self._mentors, self._mode)
        orig   = original_loads(self._students, self._mentors)
        final  = result.load_per_mentor()
        self.table.setRowCount(0)
        for m in self._mentors:
            r = self.table.rowCount()
            self.table.insertRow(r)
            o_val = orig.get(m.name, 0)
            f_val = final.get(m.name, 0)
            cap   = result.capacity
            vals  = [m.name, str(o_val), str(f_val), str(cap)]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 2:        # final load — colour-code
                    if f_val > cap:
                        item.setForeground(Qt.GlobalColor.red)
                    elif f_val == cap:
                        from PySide6.QtGui import QColor
                        item.setForeground(QColor(P.WARNING_LIGHT))
                    else:
                        from PySide6.QtGui import QColor
                        item.setForeground(QColor(P.SUCCESS_LIGHT))
                self.table.setItem(r, c, item)
        rep = imbalance_report(result)
        self.summary.setText(
            f"حالت: {self._mode.value}  |  "
            f"حداقل {rep['min']}  |  حداکثر {rep['max']}  |  "
            f"میانگین {rep['avg']}  |  "
            f"پراکندگی {rep['spread']}  |  ظرفیت {rep['capacity']}")
