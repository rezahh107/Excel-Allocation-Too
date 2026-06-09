"""Live bar chart — bars coloured by capacity status."""
from __future__ import annotations
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.utils.theme import ColorPalette as P


class DistributionChart(QWidget):
    """Horizontal bar chart: student count per mentor.

    * Blue   — load < capacity
    * Orange — load == capacity
    * Red    — load > capacity
    """

    def __init__(self) -> None:
        super().__init__()
        self.figure = Figure(figsize=(5, 3), facecolor=P.BG_SECONDARY)
        self.canvas = FigureCanvasQTAgg(self.figure)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)

    def update_chart(self, loads: dict[str, int],
                     capacity: int = 0) -> None:
        """Redraw the chart with *loads* and optional *capacity* line."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor(P.BG_SECONDARY)
        self.figure.patch.set_facecolor(P.BG_SECONDARY)

        names = list(loads.keys())
        vals  = list(loads.values())
        colors = [
            P.ERROR   if (capacity and v > capacity) else
            P.WARNING if (capacity and v == capacity) else
            P.ACCENT
            for v in vals
        ]
        bars = ax.barh(names, vals, color=colors, height=0.55)

        # value labels
        for bar, val in zip(bars, vals):
            ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", color=P.TEXT_PRIMARY, fontsize=9)

        if capacity:
            ax.axvline(capacity, color=P.WARNING_LIGHT,
                       linestyle="--", linewidth=1.4, label=f"ظرفیت ({capacity})")
            ax.legend(facecolor=P.BG_SURFACE, labelcolor=P.TEXT_PRIMARY,
                      fontsize=9)

        ax.set_xlabel("تعداد دانش‌آموز",
                      color=P.TEXT_MUTED, fontsize=10)
        ax.tick_params(colors=P.TEXT_MUTED)
        for spine in ax.spines.values():
            spine.set_edgecolor(P.BORDER)
        self.figure.tight_layout()
        self.canvas.draw()
