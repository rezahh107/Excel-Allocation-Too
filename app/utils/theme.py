"""Centralised colour palette and professional dark-gray stylesheet.

This theme intentionally avoids blue/purple as dominant UI colours.
It uses a neutral dark-gray base with subtle semantic colours.

Important:
    We avoid f-string QSS because Qt stylesheets contain many literal
    braces. Placeholder replacement is safer.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication


class ColorPalette:
    """Professional dark-gray theme colour tokens."""

    # ── backgrounds ─────────────────────────────────────────────
    BG_PRIMARY = "#111315"       # main app background
    BG_SECONDARY = "#181B1F"     # wizard pages, cards, panels
    BG_SURFACE = "#20242A"       # raised surfaces / buttons
    BG_INPUT = "#23282F"         # inputs, combo boxes, tables
    BG_HOVER = "#2B313A"         # hover states

    # ── primary accent ─────────────────────────────────────────
    # Subtle green is used only for primary actions and success-like
    # emphasis. It keeps the app neutral while making Run/Export visible.
    ACCENT = "#6FBF83"
    ACCENT_HOVER = "#86D99A"
    ACCENT_ACTIVE = "#A7D7B5"
    ACCENT_LIGHT = "#A7D7B5"

    # ── neutral accent ─────────────────────────────────────────
    NEUTRAL = "#9CA3AF"
    NEUTRAL_HOVER = "#D1D5DB"
    NEUTRAL_ACTIVE = "#F3F4F6"

    # ── semantic colours ───────────────────────────────────────
    SUCCESS = "#4B8B5F"
    SUCCESS_LIGHT = "#6FBF83"

    WARNING = "#B9822B"
    WARNING_LIGHT = "#D99A35"

    ERROR = "#B84A4A"
    ERROR_LIGHT = "#E06A6A"

    INFO = "#6B879D"
    INFO_LIGHT = "#8FA9BD"

    # ── text ───────────────────────────────────────────────────
    TEXT_PRIMARY = "#E6E9EE"
    TEXT_SECONDARY = "#C5CBD3"
    TEXT_MUTED = "#8B949E"
    TEXT_DISABLED = "#5F6772"
    TEXT_INVERSE = "#111315"

    # ── borders / misc ─────────────────────────────────────────
    BORDER = "#343A43"
    BORDER_FOCUS = "#6B7280"
    SEPARATOR = "#2A2F36"


P = ColorPalette


def _qss() -> str:
    """Return the full dark-gray QSS stylesheet string."""
    qss = """
/* ── Global ───────────────────────────────────────────────── */
QWidget {
    background-color: __BG_PRIMARY__;
    color: __TEXT_PRIMARY__;
    font-family: "Vazirmatn", "Tahoma", sans-serif;
    font-size: 13px;
}

QWizard,
QDialog {
    background-color: __BG_PRIMARY__;
}

QWizardPage {
    background-color: __BG_SECONDARY__;
    border-radius: 10px;
}

/* ── Buttons ───────────────────────────────────────────────── */
QPushButton {
    background-color: __BG_SURFACE__;
    color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER__;
    border-radius: 7px;
    padding: 7px 18px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: __BG_HOVER__;
    border-color: __BORDER_FOCUS__;
}

QPushButton:pressed {
    background-color: __BG_INPUT__;
}

QPushButton:disabled {
    background-color: __BG_SURFACE__;
    color: __TEXT_DISABLED__;
    border-color: __SEPARATOR__;
}

QPushButton#btn_primary {
    background-color: __ACCENT__;
    color: __TEXT_INVERSE__;
    border: none;
}

QPushButton#btn_primary:hover {
    background-color: __ACCENT_HOVER__;
    color: __TEXT_INVERSE__;
}

QPushButton#btn_primary:pressed {
    background-color: __ACCENT_ACTIVE__;
    color: __TEXT_INVERSE__;
}

QPushButton#btn_danger {
    background-color: __ERROR__;
    color: white;
    border: none;
}

QPushButton#btn_danger:hover {
    background-color: __ERROR_LIGHT__;
}

QPushButton#btn_secondary {
    background-color: transparent;
    color: __NEUTRAL__;
    border: 1px solid __BORDER__;
}

QPushButton#btn_secondary:hover {
    background-color: __BG_HOVER__;
    color: __NEUTRAL_HOVER__;
    border-color: __NEUTRAL__;
}

QPushButton#btn_secondary:pressed {
    background-color: __BG_INPUT__;
    color: __NEUTRAL_ACTIVE__;
}

/* ── Inputs ────────────────────────────────────────────────── */
QLineEdit,
QComboBox,
QSpinBox {
    background-color: __BG_INPUT__;
    color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER__;
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: __BG_HOVER__;
    selection-color: __TEXT_PRIMARY__;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    border-color: __BORDER_FOCUS__;
}

QComboBox QAbstractItemView {
    background-color: __BG_INPUT__;
    color: __TEXT_PRIMARY__;
    selection-background-color: __BG_HOVER__;
    selection-color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER__;
}

/* ── Tables / Trees ────────────────────────────────────────── */
QTableWidget,
QTreeWidget {
    background-color: __BG_SECONDARY__;
    alternate-background-color: __BG_PRIMARY__;
    color: __TEXT_PRIMARY__;
    gridline-color: __BORDER__;
    border: 1px solid __BORDER__;
    border-radius: 8px;
    font-family: "Vazirmatn", "Tahoma", sans-serif;
}

QTableWidget::item,
QTreeWidget::item {
    padding: 4px;
}

QTableWidget::item:selected,
QTreeWidget::item:selected {
    background-color: __BG_HOVER__;
    color: __TEXT_PRIMARY__;
}

QTableWidget::item:hover,
QTreeWidget::item:hover {
    background-color: __BG_HOVER__;
}

QHeaderView::section {
    background-color: __BG_SURFACE__;
    color: __TEXT_SECONDARY__;
    border: none;
    border-bottom: 1px solid __BORDER__;
    padding: 6px 10px;
    font-weight: bold;
}

/* ── Labels ────────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: __TEXT_PRIMARY__;
}

QLabel#lbl_title {
    font-size: 17px;
    font-weight: bold;
    color: __TEXT_PRIMARY__;
}

QLabel#lbl_muted {
    color: __TEXT_MUTED__;
    font-size: 12px;
}

QLabel#lbl_error {
    color: __ERROR_LIGHT__;
    font-weight: bold;
}

QLabel#lbl_success {
    color: __SUCCESS_LIGHT__;
    font-weight: bold;
}

QLabel#lbl_warning {
    color: __WARNING_LIGHT__;
    font-weight: bold;
}

/* ── Progress Bar ──────────────────────────────────────────── */
QProgressBar {
    background-color: __BG_SURFACE__;
    border: 1px solid __BORDER__;
    border-radius: 6px;
    text-align: center;
    color: __TEXT_PRIMARY__;
    height: 20px;
}

QProgressBar::chunk {
    background-color: __ACCENT__;
    border-radius: 5px;
}

/* ── Scroll Bars ───────────────────────────────────────────── */
QScrollBar:vertical {
    background: __BG_SECONDARY__;
    width: 9px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: __BORDER__;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: __NEUTRAL__;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: __BG_SECONDARY__;
    height: 9px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: __BORDER__;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: __NEUTRAL__;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ── Group Box ─────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid __BORDER__;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    color: __TEXT_SECONDARY__;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 8px;
    color: __TEXT_SECONDARY__;
}

/* ── Frames ────────────────────────────────────────────────── */
QFrame#card {
    background-color: __BG_SECONDARY__;
    border: 1px solid __BORDER__;
    border-radius: 10px;
}

/* ── Status Bar ────────────────────────────────────────────── */
QStatusBar {
    background-color: __BG_SURFACE__;
    color: __TEXT_MUTED__;
    border-top: 1px solid __BORDER__;
}

QStatusBar QLabel {
    color: __TEXT_MUTED__;
    padding: 0 8px;
}

/* ── RadioButton / CheckBox ────────────────────────────────── */
QRadioButton,
QCheckBox {
    color: __TEXT_PRIMARY__;
    spacing: 8px;
}

QRadioButton::indicator,
QCheckBox::indicator {
    width: 15px;
    height: 15px;
}

QRadioButton::indicator:checked,
QCheckBox::indicator:checked {
    background-color: __ACCENT__;
    border: 2px solid __ACCENT__;
    border-radius: 7px;
}

QRadioButton::indicator:unchecked,
QCheckBox::indicator:unchecked {
    background-color: __BG_INPUT__;
    border: 2px solid __BORDER__;
    border-radius: 7px;
}

/* ── Tooltip ───────────────────────────────────────────────── */
QToolTip {
    background-color: __BG_SURFACE__;
    color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER_FOCUS__;
    border-radius: 6px;
    padding: 5px 10px;
    font-family: "Vazirmatn", "Tahoma";
}

/* ── List Widget ───────────────────────────────────────────── */
QListWidget {
    background-color: __BG_SECONDARY__;
    border: 1px solid __BORDER__;
    border-radius: 6px;
    alternate-background-color: __BG_PRIMARY__;
}

QListWidget::item {
    padding: 4px;
}

QListWidget::item:selected {
    background-color: __BG_HOVER__;
    color: __TEXT_PRIMARY__;
}

QListWidget::item:hover {
    background-color: __BG_HOVER__;
}

/* ── Text Edit ─────────────────────────────────────────────── */
QTextEdit {
    background-color: __BG_INPUT__;
    color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER__;
    border-radius: 6px;
    selection-background-color: __BG_HOVER__;
    selection-color: __TEXT_PRIMARY__;
}

/* ── Wizard-specific neutral styling ───────────────────────── */
QWizard QPushButton {
    min-width: 86px;
}

QWizard QPushButton[text="بعدی"],
QWizard QPushButton[text="&Next >"] {
    background-color: __ACCENT__;
    color: __TEXT_INVERSE__;
    border: none;
}

QWizard QPushButton[text="بعدی"]:hover,
QWizard QPushButton[text="&Next >"]:hover {
    background-color: __ACCENT_HOVER__;
}

QWizard QPushButton[text="قبلی"],
QWizard QPushButton[text="< &Back"] {
    background-color: __BG_SURFACE__;
    color: __TEXT_PRIMARY__;
    border: 1px solid __BORDER__;
}
"""
    replacements = {
        "__BG_PRIMARY__": P.BG_PRIMARY,
        "__BG_SECONDARY__": P.BG_SECONDARY,
        "__BG_SURFACE__": P.BG_SURFACE,
        "__BG_INPUT__": P.BG_INPUT,
        "__BG_HOVER__": P.BG_HOVER,
        "__ACCENT__": P.ACCENT,
        "__ACCENT_HOVER__": P.ACCENT_HOVER,
        "__ACCENT_ACTIVE__": P.ACCENT_ACTIVE,
        "__ACCENT_LIGHT__": P.ACCENT_LIGHT,
        "__NEUTRAL__": P.NEUTRAL,
        "__NEUTRAL_HOVER__": P.NEUTRAL_HOVER,
        "__NEUTRAL_ACTIVE__": P.NEUTRAL_ACTIVE,
        "__SUCCESS__": P.SUCCESS,
        "__SUCCESS_LIGHT__": P.SUCCESS_LIGHT,
        "__WARNING__": P.WARNING,
        "__WARNING_LIGHT__": P.WARNING_LIGHT,
        "__ERROR__": P.ERROR,
        "__ERROR_LIGHT__": P.ERROR_LIGHT,
        "__INFO__": P.INFO,
        "__INFO_LIGHT__": P.INFO_LIGHT,
        "__TEXT_PRIMARY__": P.TEXT_PRIMARY,
        "__TEXT_SECONDARY__": P.TEXT_SECONDARY,
        "__TEXT_MUTED__": P.TEXT_MUTED,
        "__TEXT_DISABLED__": P.TEXT_DISABLED,
        "__TEXT_INVERSE__": P.TEXT_INVERSE,
        "__BORDER__": P.BORDER,
        "__BORDER_FOCUS__": P.BORDER_FOCUS,
        "__SEPARATOR__": P.SEPARATOR,
    }

    for key, value in replacements.items():
        qss = qss.replace(key, value)

    return qss


def apply_dark_theme(app: QApplication) -> None:
    """Apply the professional dark-gray theme globally."""
    app.setStyleSheet(_qss())
