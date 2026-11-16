"""Quiet desktop UI for Qt: one file to copy into an app.

The look from DESIGN.md as ready-made widgets: a frameless window with its own
title bar and sidebar, flat settings rows, a stepped popup dialog, an error
note, a toggle switch, segmented controls, a live run list with step tracks,
and inputs for durations, counts and ranges.

Copy this file into your project as it is and build pages from its widgets.
Change the colours only through TOKENS.

Works with PySide6 or PyQt5. It uses the binding your app already imported,
otherwise PySide6, then PyQt5. Set QUIET_QT=pyqt5 or QUIET_QT=pyside6 to choose.

    from quiet_ui import make_app, QuietWindow, Page, button, run_app

    app = make_app()
    win = QuietWindow("My app")
    page = Page("Run", "What this page is for.")
    page.add_action(button("Start run", "primary", icon_kind="play"))
    win.add_page("Run", "play", page)
    win.show()
    run_app(app)
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
from pathlib import Path
from string import Template
from typing import Callable, Iterable, Sequence


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------
def _import_qt():
    order = ["pyside6", "pyqt5"]
    if "PyQt5.QtWidgets" in sys.modules:
        order = ["pyqt5", "pyside6"]
    elif "PySide6.QtWidgets" in sys.modules:
        order = ["pyside6", "pyqt5"]
    wanted = os.environ.get("QUIET_QT", "").strip().lower()
    if wanted in order:
        order.sort(key=lambda name: name != wanted)
    problems = []
    for name in order:
        try:
            if name == "pyside6":
                from PySide6 import QtCore, QtGui, QtWidgets
                return name, QtCore, QtGui, QtWidgets, QtCore.Signal
            from PyQt5 import QtCore, QtGui, QtWidgets
            return name, QtCore, QtGui, QtWidgets, QtCore.pyqtSignal
        except ImportError as exc:
            problems.append(f"{name}: {exc}")
    raise ImportError("quiet_ui needs PySide6 or PyQt5 (" + "; ".join(problems) + ")")


QT_API, QtCore, QtGui, QtWidgets, Signal = _import_qt()

Qt = QtCore.Qt
QEvent, QPoint, QPointF, QRect, QRectF, QSize, QTimer = (
    QtCore.QEvent, QtCore.QPoint, QtCore.QPointF, QtCore.QRect, QtCore.QRectF, QtCore.QSize, QtCore.QTimer)
QVariantAnimation = QtCore.QVariantAnimation
QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPolygonF = (
    QtGui.QColor, QtGui.QFont, QtGui.QIcon, QtGui.QPainter, QtGui.QPainterPath, QtGui.QPalette,
    QtGui.QPen, QtGui.QPixmap, QtGui.QPolygonF)
W = QtWidgets
QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog = (
    W.QApplication, W.QButtonGroup, W.QCheckBox, W.QComboBox, W.QDialog)
QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit = (
    W.QDoubleSpinBox, W.QFrame, W.QGridLayout, W.QHBoxLayout, W.QLabel, W.QLineEdit)
QListView, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton = (
    W.QListView, W.QMainWindow, W.QMessageBox, W.QPlainTextEdit, W.QProgressBar, W.QPushButton,
    W.QRadioButton)
QScrollArea, QSizeGrip, QSpinBox, QStackedWidget, QStyledItemDelegate = (
    W.QScrollArea, W.QSizeGrip, W.QSpinBox, W.QStackedWidget, W.QStyledItemDelegate)
QVBoxLayout, QWidget, QGraphicsDropShadowEffect = (
    W.QVBoxLayout, W.QWidget, W.QGraphicsDropShadowEffect)


def _iv(value) -> int:
    """An enum or flag as an int, on any binding."""
    return int(getattr(value, "value", value))


def _global_pos(event):
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def run_dialog(dialog) -> int:
    """Shows a dialog modally and returns its result (exec on PySide6, exec_ on PyQt5)."""
    run = getattr(dialog, "exec", None) or dialog.exec_
    return run()


def run_app(app) -> int:
    run = getattr(app, "exec", None) or app.exec_
    return run()


# ---------------------------------------------------------------------------
# Tokens and stylesheet
# ---------------------------------------------------------------------------
TOKENS = {
    "bg": "#1d1d1f",          # page and title bar
    "side": "#161618",        # sidebar
    "raise": "#232326",       # dialogs, menus, popups, notes
    "hover": "#2a2a2e",
    "active": "#323236",      # selected or pressed
    "line": "#2e2e33",        # dividers and input borders
    "track": "#3a3a40",       # rails, switch track, hover border
    "seg": "#1b1b1e",         # segmented control track
    "text": "#ecebe7",
    "muted": "#9b9a95",
    "faint": "#6c6b67",
    "off": "#4a4946",         # disabled text and icons
    "log": "#c9c8c3",         # log text
    "accent": "#5ed082",
    "accent_hover": "#6ddb90",
    "accent_pressed": "#4cbf71",
    "accent_text": "#0b1a10",
    "good": "#5ed082",
    "win": "#4cb4ff",
    "bad": "#e84057",
    "warn": "#e0a83a",
    "close": "#c42b1c",       # window Close button on hover
}

if sys.platform == "win32":
    _FONTS = {
        "font": '"Segoe UI", sans-serif',
        "strong": 'font-family: "Segoe UI Semibold"; font-weight: normal',
        "mono": '"Cascadia Mono", "Consolas", monospace',
    }
else:
    _FONTS = {
        "font": "system-ui, sans-serif",
        "strong": "font-weight: 600",
        "mono": '"SF Mono", "DejaVu Sans Mono", monospace',
    }

_QSS = Template("""
* { font-family: $font; font-size: 14px; color: $text; outline: none; }
QToolTip { background-color: $hover; color: $text; border: 1px solid $track; padding: 6px 8px; border-radius: 6px; }

#WindowFrame { background-color: $bg; border: 1px solid $line; border-radius: 10px; }
#WindowFrame[maximized="true"] { border-radius: 0; border: none; }
#TitleBar { background-color: transparent; border: none; }
#TitleLabel { color: $text; font-size: 14px; $strong; }
#TitleButton { background: transparent; border: none; border-radius: 0; padding: 0; }

#Sidebar { background-color: $side; border-right: 1px solid $line; border-bottom-left-radius: 10px; }
#Sidebar[maximized="true"] { border-bottom-left-radius: 0; }
#NavSection { color: $faint; font-size: 12px; $strong; padding: 0 10px 6px 10px; }
#NavButton { background: transparent; border: none; border-radius: 8px; color: $text;
    text-align: left; padding: 9px 12px; font-size: 15px; font-weight: 500; }
#NavButton:hover { background-color: $hover; }
#NavButton:checked { background-color: $active; }
#NavButton:disabled { color: $off; }
#SidebarStatus { background: transparent; border: none; border-top: 1px solid $line; border-radius: 0; }
#SidebarStatusText { color: $text; font-size: 13px; font-weight: 500; }
#SidebarVersion { color: $faint; font-size: 12px; }

#Content { background-color: $bg; border-bottom-right-radius: 10px; }
#Content[maximized="true"] { border-bottom-right-radius: 0; }
#PageBody { background: transparent; }

#PageTitle { color: $text; font-size: 26px; $strong; }
#PageSubtitle { color: $muted; font-size: 14px; }
#SettingsHeading { color: $text; font-size: 15px; $strong; }
#SectionSub { color: $faint; font-size: 13px; }
#SettingRow { background: transparent; }
#RowLabel { color: $text; font-size: 14px; $strong; }
#RowLabel:disabled { color: $off; }
#RowHelp { color: $faint; font-size: 13px; }
#RowHelp:disabled { color: $track; }
#RowHelp[state="on"] { color: $good; }
#RowHelp[state="off"] { color: $warn; }
#FormLabel { color: $muted; font-size: 13px; }
#Eyebrow { color: $faint; font-size: 11px; $strong; letter-spacing: 1px; }
#Summary { color: $text; font-size: 13px; }
#Note { color: $muted; font-size: 13px; }
#Note:disabled { color: $off; }
#MonoValue { color: $text; font-family: $mono; font-size: 13px; }
#MetaText { color: $faint; font-size: 13px; }
#CountText { color: $muted; font-size: 13px; font-weight: 500; }
#GoodText { color: $good; font-size: 13px; }
#BadText { color: $bad; font-size: 13px; }
#WarnText { color: $warn; font-size: 13px; }
#Divider { background-color: $line; border: none; min-height: 1px; max-height: 1px; }
#VDivider { background-color: $line; border: none; min-width: 1px; max-width: 1px; }

#SegTrack { background-color: $seg; border: none; border-radius: 10px; }
#SegButton { background: transparent; border: none; border-radius: 8px; color: $muted;
    padding: 5px 14px; font-size: 13px; font-weight: 500; }
#SegButton:hover { background-color: $hover; color: $text; }
#SegButton:checked { background-color: $active; color: $text; }
#SegButton:disabled { color: $off; }
#Tabs { background: transparent; border: none; }
#ViewTab { background: transparent; border: none; border-radius: 8px; color: $faint;
    padding: 5px 10px; font-size: 14px; $strong; }
#ViewTab:hover { color: $text; }
#ViewTab:checked { background-color: $hover; color: $text; }

#OptionRow { background: transparent; border: none; border-radius: 8px; }
#OptionRow:hover { background-color: $hover; }
#OptionRow[selected="true"] { background-color: $active; }
#OptionTitle { color: $text; font-size: 14px; $strong; }
#OptionDesc { color: $muted; font-size: 13px; }
#OptionKey { color: $faint; font-size: 13px; font-family: $mono; }
#OptionTitle:disabled, #OptionDesc:disabled { color: $off; }

#DialogFrame { background-color: $raise; border: 1px solid $line; border-radius: 12px; }
#DialogHeaderTitle { color: $text; font-size: 15px; $strong; }
#DialogCrumb { color: $muted; font-size: 13px; }
#DialogNav { background: transparent; }
#StepText { color: $faint; font-size: 12px; $strong; }
#DialogMessage { color: $muted; font-size: 13px; }
#DialogMessage[state="bad"] { color: $bad; }
#DialogMessage[state="good"] { color: $good; }

#ErrorNote { background-color: $raise; border: 1px solid $track; border-radius: 10px; }
#NoteTitle { color: $text; font-size: 13px; $strong; }
#NoteText { color: $muted; font-size: 12px; }

#StatusButton { background: transparent; border: none; padding: 6px 8px; font-size: 13px;
    font-weight: 500; color: $faint; text-align: right; }
#StatusButton[state="warn"] { color: $warn; }
#StatusButton[state="warn"]:hover { background-color: $hover; border-radius: 6px; }
#StatusButton[state="dirty"] { color: $muted; }
#StatusButton[state="ok"] { color: $good; }

#ItemName { color: $text; font-size: 14px; $strong; }
#ItemSub { color: $faint; font-size: 12px; }
#ItemStatus, #ItemResult { color: $muted; font-size: 12px; }
#ItemStatus[state="ok"], #ItemResult[state="ok"] { color: $good; }
#ItemStatus[state="bad"], #ItemResult[state="bad"] { color: $bad; }
#ItemStatus[state="warn"], #ItemResult[state="warn"] { color: $warn; }
#Stat { background: transparent; border: none; }
#StatTitle { color: $faint; font-size: 13px; font-weight: 500; }
#StatNumber { color: $text; font-size: 26px; $strong; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: transparent; border: 1px solid $line; border-radius: 8px;
    padding: 6px 10px; color: $text; min-height: 20px;
    selection-background-color: $accent; selection-color: $accent_text;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: $track; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: $accent; }
QLineEdit[invalid="true"] { border-color: $bad; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    border-color: $line; color: $faint; }
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: transparent; border: none; width: 18px; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url($up); width: 9px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url($down); width: 9px; height: 9px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { image: url($down); width: 9px; height: 9px; margin-right: 8px; }
QComboBox { combobox-popup: 0; }
#ComboPopup { background-color: $raise; border: 1px solid $line; border-radius: 10px; }
QComboBox QAbstractItemView { background-color: $raise; border: none; outline: 0; color: $text;
    padding: 4px; selection-background-color: $active; selection-color: $text; }
QComboBox QAbstractItemView::item { min-height: 28px; padding: 0 10px; border-radius: 8px; color: $text; }
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {
    background-color: $hover; color: $text; }

QCheckBox { color: $text; spacing: 8px; padding: 2px 0; }
QCheckBox:disabled { color: $faint; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid $track; border-radius: 5px;
    background-color: transparent; }
QCheckBox::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked { background-color: $accent; border-color: $accent; image: url($check); }
QCheckBox::indicator:disabled { border-color: $line; background-color: $bg; }

#PrimaryButton {
    background: $accent;
    color: $accent_text; border: none; border-radius: 8px; padding: 7px 14px; font-size: 14px;
    min-height: 18px; $strong; }
#PrimaryButton:hover { background: $accent_hover; }
#PrimaryButton:pressed { background: $accent_pressed; }
#PrimaryButton:disabled { background: $hover; color: $faint; }
#SecondaryButton { background: transparent; color: $text; border: 1px solid $line; border-radius: 8px;
    padding: 6px 12px; font-weight: 500; min-height: 18px; }
#SecondaryButton:hover { background-color: $hover; border-color: $track; }
#SecondaryButton:disabled { color: $off; }
#DangerButton { background: transparent; color: $bad; border: 1px solid $line; border-radius: 8px;
    padding: 6px 14px; min-height: 18px; $strong; }
#DangerButton:hover { background-color: $hover; border-color: $track; }
#DangerButton:disabled { color: $off; }
#GhostButton { background: transparent; border: none; border-radius: 8px; color: $muted;
    padding: 6px 10px; font-size: 13px; font-weight: 500; }
#GhostButton:hover { background-color: $hover; color: $text; }
#GhostButton:checked { background-color: $active; color: $text; }
#GhostButton:disabled { color: $off; }
#GhostButton[state="warn"] { color: $warn; }

QProgressBar { background-color: $track; border: none; border-radius: 2px; min-height: 4px; max-height: 4px; }
QProgressBar::chunk { background-color: $accent; border-radius: 2px; }

QPlainTextEdit { background-color: transparent; border: 1px solid $line; border-radius: 8px; color: $log;
    font-family: $mono; font-size: 13px; padding: 10px;
    selection-background-color: $accent; selection-color: $accent_text; }
QPlainTextEdit:focus { border-color: $accent; }
QPlainTextEdit:disabled { color: $faint; }
#LogView { border: none; border-radius: 0; padding: 10px 14px; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(236, 235, 231, 30); border-radius: 4px; min-height: 40px; }
QScrollBar::handle:vertical:hover { background: rgba(236, 235, 231, 80); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: rgba(236, 235, 231, 30); border-radius: 4px; min-width: 40px; }
QScrollBar::handle:horizontal:hover { background: rgba(236, 235, 231, 80); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

QMenu { background-color: $raise; border: 1px solid $line; border-radius: 8px; padding: 4px; }
QMenu::item { color: $text; padding: 6px 14px; border-radius: 6px; font-size: 13px; }
QMenu::item:selected { background-color: $active; }

QMessageBox { background-color: $raise; }
QMessageBox QLabel { color: $text; }
QMessageBox QPushButton { background: transparent; color: $text; border: 1px solid $line;
    border-radius: 8px; padding: 7px 14px; min-width: 70px; }
QMessageBox QPushButton:hover { background-color: $hover; }
""")


def _round_pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _poly(*points: tuple[float, float]) -> QPolygonF:
    return QPolygonF([QPointF(x, y) for x, y in points])


_ASSETS: dict[str, str] = {}


def _stylesheet_assets() -> dict[str, str]:
    """QSS cannot draw icons: the checkmark and the spin and dropdown arrows are painted once
    into PNGs in the temp folder, and the stylesheet points at them."""
    if _ASSETS:
        return _ASSETS
    folder = Path(tempfile.gettempdir())

    def save(name: str, draw: Callable[[QPainter], None]) -> str:
        pix = QPixmap(36, 36)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        draw(p)
        p.end()
        path = folder / name
        pix.save(str(path), "PNG")
        return path.as_posix()

    def check(p: QPainter) -> None:
        p.setPen(_round_pen(TOKENS["accent_text"], 4.5))
        p.drawPolyline(_poly((9, 19), (15.5, 25), (27, 11)))

    def arrow(up: bool) -> Callable[[QPainter], None]:
        def draw(p: QPainter) -> None:
            p.setPen(_round_pen(TOKENS["muted"], 4.5))
            y0, y1 = (23, 13) if up else (13, 23)
            p.drawPolyline(_poly((9, y0), (18, y1), (27, y0)))
        return draw

    _ASSETS["check"] = save("quiet_ui_check.png", check)
    _ASSETS["up"] = save("quiet_ui_up.png", arrow(True))
    _ASSETS["down"] = save("quiet_ui_down.png", arrow(False))
    return _ASSETS


def stylesheet() -> str:
    """The whole app stylesheet, from TOKENS. Needs a QApplication to exist."""
    return _QSS.substitute({**TOKENS, **_FONTS, **_stylesheet_assets()})


def apply_theme(app) -> None:
    """Fusion style, a dark palette for anything the stylesheet does not reach, and the stylesheet."""
    app.setStyle("Fusion")
    pal = app.palette()
    for role, key in (
        (QPalette.Window, "bg"), (QPalette.Base, "bg"), (QPalette.AlternateBase, "raise"),
        (QPalette.Button, "raise"), (QPalette.ToolTipBase, "raise"), (QPalette.WindowText, "text"),
        (QPalette.Text, "text"), (QPalette.ButtonText, "text"), (QPalette.ToolTipText, "text"),
        (QPalette.Highlight, "accent"), (QPalette.HighlightedText, "accent_text"),
    ):
        pal.setColor(role, QColor(TOKENS[key]))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet())


def make_app(argv: Sequence[str] | None = None):
    """Creates the QApplication (high-DPI on for PyQt5) with the theme applied."""
    app = QApplication.instance()
    if app is None:
        if QT_API == "pyqt5":
            for name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
                if hasattr(Qt, name):
                    QApplication.setAttribute(getattr(Qt, name), True)
        app = QApplication(list(argv if argv is not None else sys.argv))
    apply_theme(app)
    return app


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def repolish(widget: QWidget) -> None:
    """Re-applies the stylesheet after a dynamic property changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_state(widget: QWidget, state: str = "") -> None:
    """Sets the `state` property ("ok", "bad", "warn", "dirty", "on", "off" or "") and re-polishes."""
    widget.setProperty("state", state or "")
    repolish(widget)


def label(text: str = "", kind: str = "", wrap: bool = False) -> QLabel:
    """A QLabel with an object name from the stylesheet: PageTitle, RowLabel, RowHelp, Note, ..."""
    lab = QLabel(text)
    if kind:
        lab.setObjectName(kind)
    lab.setWordWrap(wrap)
    return lab


class Divider(QFrame):
    """A 1px line in --line, horizontal by default."""

    def __init__(self, vertical: bool = False):
        super().__init__()
        self.setObjectName("VDivider" if vertical else "Divider")
        if vertical:
            self.setFixedWidth(1)
        else:
            self.setFixedHeight(1)


def status_dot(color: str, size: int = 8) -> QLabel:
    dot = QLabel()
    dot.setFixedSize(size, size)
    set_dot(dot, color)
    return dot


def set_dot(dot: QLabel, color: str) -> None:
    dot.setStyleSheet(f"background-color: {color}; border-radius: {dot.width() // 2}px;")


def rough_duration(seconds: float) -> str:
    """How long, roughly: 45 s, 12 min, 1 h 46 min, 2 days 3 h."""
    s = max(0, int(round(seconds)))
    if s < 60:
        return f"{s} s"
    m = s // 60
    if m < 60:
        return f"{m} min"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h} h {m} min" if m else f"{h} h"
    d, h = divmod(h, 24)
    days = f"{d} day{'s' if d != 1 else ''}"
    return f"{days} {h} h" if h else days


def short_id(text: str, head: int = 4, tail: int = 4) -> str:
    """A long id shortened in the middle: Ab12…xY9z."""
    text = str(text or "")
    return f"{text[:head]}…{text[-tail:]}" if len(text) > head + tail + 2 else text


# ---------------------------------------------------------------------------
# Icons (16px outline, 1.5px round stroke, drawn at 3x)
# ---------------------------------------------------------------------------
ICONS = ("sliders", "play", "stop", "copy", "chart", "user", "globe", "image", "gear", "folder",
         "edit", "trash", "list", "upload", "check")


def icon_pixmap(kind: str, color: str, size: int = 16) -> QPixmap:
    scale = 3
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(scale * size / 16.0, scale * size / 16.0)
    p.setPen(_round_pen(color, 1.5))
    p.setBrush(Qt.NoBrush)
    if kind == "sliders":
        for y, kx in ((4, 10.5), (8, 5.5), (12, 9)):
            p.drawLine(QPointF(2.5, y), QPointF(kx - 1.8, y))
            p.drawLine(QPointF(kx + 1.8, y), QPointF(13.5, y))
            p.drawEllipse(QPointF(kx, y), 1.8, 1.8)
    elif kind == "play":
        p.setBrush(QColor(color))
        p.drawPolygon(_poly((5, 3.5), (12.5, 8), (5, 12.5)))
    elif kind == "stop":
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(4.5, 4.5, 7, 7), 1.2, 1.2)
    elif kind == "copy":
        p.drawRoundedRect(QRectF(5.5, 5.5, 7.5, 7.5), 1.5, 1.5)
        p.drawPolyline(_poly((3, 10.5), (3, 3.5), (3.5, 3), (10.5, 3)))
    elif kind == "chart":
        p.drawPolyline(_poly((2.5, 11.5), (6, 7.5), (9, 10), (13.5, 4.5)))
        p.drawPolyline(_poly((10.5, 4.5), (13.5, 4.5), (13.5, 7.5)))
    elif kind == "user":
        p.drawEllipse(QPointF(8, 5.5), 2.6, 2.6)
        path = QPainterPath()
        path.moveTo(3, 13.5)
        path.cubicTo(3, 10.2, 5.2, 9.2, 8, 9.2)
        path.cubicTo(10.8, 9.2, 13, 10.2, 13, 13.5)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "globe":
        p.drawEllipse(QPointF(8, 8), 5.5, 5.5)
        p.drawEllipse(QPointF(8, 8), 2.3, 5.5)
        p.drawLine(QPointF(2.5, 8), QPointF(13.5, 8))
    elif kind == "image":
        p.drawRoundedRect(QRectF(2.5, 3, 11, 10), 2, 2)
        p.drawEllipse(QPointF(6, 6.5), 1.2, 1.2)
        p.drawPolyline(_poly((2.8, 11.5), (6.5, 8.5), (9, 10.5), (13.2, 7)))
    elif kind == "gear":
        p.drawEllipse(QPointF(8, 8), 2.0, 2.0)
        path = QPainterPath()
        for k in range(16):
            a = math.pi * 2 * k / 16
            r = 5.6 if k % 2 == 0 else 4.4
            pt = QPointF(8 + r * math.cos(a), 8 + r * math.sin(a))
            path.moveTo(pt) if k == 0 else path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "folder":
        p.drawPolyline(_poly((2.5, 12.5), (2.5, 4), (6.5, 4), (8, 5.5), (13.5, 5.5), (13.5, 12.5),
                             (2.5, 12.5)))
    elif kind == "edit":
        p.drawPolyline(_poly((3, 13), (3.5, 10.5), (10.5, 3.5), (12.5, 5.5), (5.5, 12.5), (3, 13)))
        p.drawLine(QPointF(9, 5), QPointF(11, 7))
    elif kind == "trash":
        p.drawLine(QPointF(3, 4.5), QPointF(13, 4.5))
        p.drawPolyline(_poly((6.5, 4.5), (6.5, 3), (9.5, 3), (9.5, 4.5)))
        p.drawRoundedRect(QRectF(4.5, 4.5, 7, 8.5), 1.2, 1.2)
    elif kind == "list":
        for y in (4.5, 8, 11.5):
            p.drawLine(QPointF(6, y), QPointF(13.5, y))
            p.drawPoint(QPointF(3, y))
    elif kind == "upload":
        p.drawLine(QPointF(8, 2.8), QPointF(8, 10))
        p.drawPolyline(_poly((4.8, 6), (8, 2.8), (11.2, 6)))
        p.drawPolyline(_poly((3, 10.5), (3, 13), (13, 13), (13, 10.5)))
    elif kind == "check":
        p.drawPolyline(_poly((3.5, 8.5), (6.5, 11.5), (12.5, 4.5)))
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


def icon(kind: str, color: str | None = None, disabled: str | None = None, size: int = 16) -> QIcon:
    """An outline icon with a dimmed disabled state."""
    ic = QIcon()
    normal = icon_pixmap(kind, color or TOKENS["text"], size)
    for mode in (QIcon.Normal, QIcon.Active, QIcon.Selected):
        for state in (QIcon.Off, QIcon.On):
            ic.addPixmap(normal, mode, state)
    off = icon_pixmap(kind, disabled or TOKENS["off"], size)
    ic.addPixmap(off, QIcon.Disabled, QIcon.Off)
    ic.addPixmap(off, QIcon.Disabled, QIcon.On)
    return ic


def check_badge(size: int = 18) -> QPixmap:
    """A filled accent circle with a dark tick: the chosen option."""
    scale = 3
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(TOKENS["accent"]))
    p.drawEllipse(QRectF(0, 0, size * scale, size * scale))
    p.setPen(_round_pen(TOKENS["accent_text"], 2.0 * scale))
    k = size * scale / 18.0
    p.drawPolyline(_poly((5.2 * k, 9.4 * k), (7.9 * k, 12.0 * k), (12.9 * k, 6.5 * k)))
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


def app_mark(size: int = 20, color: str | None = None) -> QPixmap:
    """A placeholder logo: a rounded accent square with a dark dot. Replace it with yours."""
    scale = 3
    s = size * scale
    pix = QPixmap(s, s)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color or TOKENS["accent"]))
    p.drawRoundedRect(QRectF(0, 0, s, s), s / 3, s / 3)
    p.setBrush(QColor(TOKENS["accent_text"]))
    p.drawEllipse(QRectF(s / 4, s / 4, s / 2, s / 2))
    p.end()
    pix.setDevicePixelRatio(scale)
    return pix


def round_pixmap(data: bytes = b"", text: str = "?", size: int = 36,
                 bg: str | None = None, fg: str | None = None) -> QPixmap:
    """A round avatar: the picture in `data`, or the first letter of `text` on --hover."""
    scale = 3
    s = size * scale
    out = QPixmap(s, s)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addEllipse(0, 0, s, s)
    p.setClipPath(path)
    src = QPixmap()
    if data and src.loadFromData(data):
        src = src.scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap((s - src.width()) // 2, (s - src.height()) // 2, src)
    else:
        p.fillRect(0, 0, s, s, QColor(bg or TOKENS["hover"]))
        p.setPen(QColor(fg or TOKENS["muted"]))
        font = QFont("Segoe UI Semibold" if sys.platform == "win32" else "")
        font.setPixelSize(int(size * 0.42) * scale)
        if sys.platform != "win32":
            font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, (str(text or "?").lstrip("@")[:1] or "?").upper())
    p.end()
    out.setDevicePixelRatio(scale)
    return out


def button(text: str = "", kind: str = "ghost", icon_kind: str | None = None,
           on_click: Callable[[], None] | None = None, tooltip: str = "") -> QPushButton:
    """kind: primary (one per screen), secondary (outline), danger (outline, red text) or ghost."""
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    if tooltip:
        btn.setToolTip(tooltip)
    set_button_kind(btn, kind, icon_kind)
    if on_click is not None:
        btn.clicked.connect(lambda _=False: on_click())
    return btn


_BUTTON_NAMES = {"primary": "PrimaryButton", "secondary": "SecondaryButton",
                 "danger": "DangerButton", "ghost": "GhostButton"}


def set_button_kind(btn: QPushButton, kind: str, icon_kind: str | None = None) -> None:
    """Turns a button into another kind, for example Start run (primary) into Stop (danger)."""
    btn.setObjectName(_BUTTON_NAMES.get(kind, "GhostButton"))
    if icon_kind:
        color = {"primary": TOKENS["accent_text"], "danger": TOKENS["bad"],
                 "secondary": TOKENS["text"]}.get(kind, TOKENS["muted"])
        btn.setIcon(icon(icon_kind, color, TOKENS["faint"]))
        btn.setIconSize(QSize(16, 16))
    repolish(btn)


def log_view(placeholder: str = "Output will appear here once you start a run.") -> QPlainTextEdit:
    view = QPlainTextEdit()
    view.setObjectName("LogView")
    view.setReadOnly(True)
    view.setMaximumBlockCount(8000)
    view.setPlaceholderText(placeholder)
    return view


# ---------------------------------------------------------------------------
# Inputs that ignore the mouse wheel unless focused
# ---------------------------------------------------------------------------
class NoWheelSpinBox(QSpinBox):
    def __init__(self, minimum: int = 0, maximum: int = 1_000_000, value: int = 0, suffix: str = ""):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setRange(minimum, maximum)
        self.setValue(value)
        if suffix:
            self.setSuffix(suffix)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, minimum: float = 0.0, maximum: float = 1_000_000.0, value: float = 0.0,
                 decimals: int = 2, suffix: str = ""):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setDecimals(decimals)
        self.setRange(minimum, maximum)
        self.setValue(value)
        if suffix:
            self.setSuffix(suffix)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class NoWheelComboBox(QComboBox):
    def __init__(self, items: Iterable = ()):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self._popup_styled = False
        for item in items:
            if isinstance(item, tuple):
                self.addItem(str(item[0]), item[1])
            else:
                self.addItem(str(item))

    def showPopup(self):
        if not self._popup_styled:
            self._popup_styled = True
            style_combo_popup(self)
        super().showPopup()

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


def style_combo_popup(combo: QComboBox) -> None:
    """A flat list popup on --raise, without the native frame and shadow."""
    combo.setView(QListView())
    combo.setItemDelegate(QStyledItemDelegate(combo))
    combo.setMaxVisibleItems(10)
    view = combo.view()
    view.setFrameShape(QFrame.NoFrame)
    popup = view.window()
    popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
    popup.setObjectName("ComboPopup")
    popup.setAttribute(Qt.WA_TranslucentBackground, False)
    dark = QColor(TOKENS["raise"])
    for wdg in (popup, view.viewport()):
        pal = wdg.palette()
        for role in (QPalette.Window, QPalette.Base):
            pal.setColor(role, dark)
        wdg.setPalette(pal)
        wdg.setAutoFillBackground(True)
    popup.setStyleSheet(f"#ComboPopup {{ background-color: {TOKENS['raise']}; "
                        f"border: 1px solid {TOKENS['line']}; }}")


# ---------------------------------------------------------------------------
# Toggle switch, segmented control, options, distribution bar
# ---------------------------------------------------------------------------
class ToggleSwitch(QCheckBox):
    """A 36x20 switch: the track fades --track to --accent, the knob --muted to --bg, in 0.12s."""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(36, 20)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.valueChanged.connect(self._set_pos)
        self.toggled.connect(self._animate)
        self.setChecked(checked)
        self._pos = 1.0 if checked else 0.0

    def _set_pos(self, v) -> None:
        self._pos = float(v)
        self.update()

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        if not self.isVisible():
            self._set_pos(1.0 if on else 0.0)
            return
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def showEvent(self, e):
        self._set_pos(1.0 if self.isChecked() else 0.0)
        super().showEvent(e)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    @staticmethod
    def _mix(a: str, b: str, t: float) -> QColor:
        ca, cb = QColor(a), QColor(b)
        return QColor(int(ca.red() + (cb.red() - ca.red()) * t),
                      int(ca.green() + (cb.green() - ca.green()) * t),
                      int(ca.blue() + (cb.blue() - ca.blue()) * t))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.35)
        w, h, t = self.width(), self.height(), self._pos
        p.setPen(Qt.NoPen)
        p.setBrush(self._mix(TOKENS["track"], TOKENS["accent"], t))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        d = h - 6
        p.setBrush(self._mix(TOKENS["muted"], TOKENS["bg"], t))
        p.drawEllipse(QRectF(3 + (w - 6 - d) * t, 3, d, d))
        p.end()


class Segmented(QFrame):
    """Two to four choices side by side. tabs=True gives the quieter tab look ("Items · Log")."""

    changed = Signal(int)

    def __init__(self, names: Sequence[str], index: int = 0, tabs: bool = False):
        super().__init__()
        self.setObjectName("Tabs" if tabs else "SegTrack")
        lay = QHBoxLayout(self)
        pad = 0 if tabs else 3
        lay.setContentsMargins(pad, pad, pad, pad)
        lay.setSpacing(4 if tabs else 2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []
        for i, name in enumerate(names):
            b = QPushButton(name)
            b.setObjectName("ViewTab" if tabs else "SegButton")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        if tabs:
            lay.addStretch()
        self.group.buttonClicked.connect(lambda b: self.changed.emit(self.buttons.index(b)))
        if self.buttons:
            self.buttons[max(0, min(index, len(self.buttons) - 1))].setChecked(True)

    def index(self) -> int:
        for i, b in enumerate(self.buttons):
            if b.isChecked():
                return i
        return -1

    def set_index(self, index: int) -> None:
        if 0 <= index < len(self.buttons) and not self.buttons[index].isChecked():
            self.buttons[index].setChecked(True)
            self.changed.emit(index)

    def set_text(self, index: int, text: str) -> None:
        self.buttons[index].setText(text)

    def set_enabled(self, index: int, on: bool, tooltip: str = "") -> None:
        self.buttons[index].setEnabled(on)
        self.buttons[index].setToolTip(tooltip)


class OptionRow(QFrame):
    """One choice like a menu item: a title, what it does, a check when chosen and its number key.
    The whole row is clickable."""

    clicked = Signal()

    def __init__(self, title: str, desc: str = "", number: int = 0):
        super().__init__()
        self.setObjectName("OptionRow")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(14)
        self.radio = QRadioButton()  # never drawn; it keeps the group exclusive
        self.radio.hide()
        text = QVBoxLayout()
        text.setSpacing(3)
        self.title = label(title, "OptionTitle")
        self.desc = label(desc, "OptionDesc", wrap=True)
        self.desc.setVisible(bool(desc))
        text.addWidget(self.title)
        text.addWidget(self.desc)
        lay.addLayout(text, 1)
        self.check = QLabel()
        self.check.setPixmap(check_badge(18))
        self.check.setFixedSize(18, 18)
        self.check.setVisible(False)
        lay.addWidget(self.check, 0, Qt.AlignTop)
        self.key = label(str(number) if number else "", "OptionKey")
        self.key.setFixedWidth(12)
        lay.addWidget(self.key, 0, Qt.AlignTop)
        self.radio.toggled.connect(self._mark)

    def _mark(self, on: bool) -> None:
        self.setProperty("selected", on)
        self.check.setVisible(on)
        repolish(self)

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.radio.setChecked(True)
            self.clicked.emit()
        super().mousePressEvent(event)


class OptionList(QWidget):
    """A column of OptionRows; in a StepDialog the number keys pick them."""

    changed = Signal(int)

    def __init__(self, options: Sequence[tuple[str, str]], index: int = 0):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.rows: list[OptionRow] = []
        for i, (title, desc) in enumerate(options):
            row = OptionRow(title, desc, i + 1 if i < 9 else 0)
            self.group.addButton(row.radio, i)
            row.clicked.connect(lambda i=i: self.changed.emit(i))
            lay.addWidget(row)
            self.rows.append(row)
        if self.rows:
            self.rows[max(0, min(index, len(self.rows) - 1))].radio.setChecked(True)

    def index(self) -> int:
        for i, row in enumerate(self.rows):
            if row.radio.isChecked():
                return i
        return -1

    def set_index(self, index: int) -> None:
        if 0 <= index < len(self.rows) and self.rows[index].isEnabled():
            self.rows[index].radio.setChecked(True)
            self.changed.emit(index)


class DistributionBar(QWidget):
    """An 8px bar split into coloured parts: set_parts([(percent, colour), ...])."""

    COLORS = (TOKENS["accent"], TOKENS["win"], TOKENS["warn"], TOKENS["bad"], "#c4b5fd", "#fb923c")

    def __init__(self, parts: Sequence[tuple[float, str]] = ()):
        super().__init__()
        self.setFixedHeight(8)
        self.parts = list(parts)

    def set_parts(self, parts: Sequence[tuple[float, str]]) -> None:
        self.parts = list(parts)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.35)
        r = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(r, 4, 4)
        p.setClipPath(path)
        p.fillRect(r, QColor(TOKENS["track"]))
        x = 0.0
        for pct, color in self.parts:
            w = r.width() * max(0.0, pct) / 100.0
            if w <= 0:
                continue
            p.fillRect(QRectF(x, 0, w, r.height()), QColor(color))
            x += w
            p.fillRect(QRectF(x - 1, 0, 2, r.height()), QColor(TOKENS["raise"]))
        p.end()


def legend(parts: Sequence[tuple[str, str]]) -> QWidget:
    """A faint legend under a DistributionBar: [(text, colour), ...]."""
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)
    for text, color in parts:
        item = QHBoxLayout()
        item.setSpacing(6)
        item.addWidget(status_dot(color, 8), 0, Qt.AlignVCenter)
        item.addWidget(label(text, "MetaText"))
        lay.addLayout(item)
    lay.addStretch()
    return box


# ---------------------------------------------------------------------------
# Number inputs people can read
# ---------------------------------------------------------------------------
class DurationInput(QWidget):
    """A number and a unit (seconds / minutes / hours) instead of raw seconds."""

    changed = Signal(float)
    UNITS = (("seconds", 1), ("minutes", 60), ("hours", 3600))

    def __init__(self, seconds: float = 0, maximum: int = 1_000_000):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.spin = NoWheelSpinBox(0, maximum)
        self.spin.setFixedWidth(84)
        self.unit = NoWheelComboBox(self.UNITS)
        lay.addWidget(self.spin)
        lay.addWidget(self.unit)
        lay.addStretch()
        self.set_seconds(seconds)
        self.spin.valueChanged.connect(lambda _v: self.changed.emit(self.seconds()))
        self.unit.currentIndexChanged.connect(lambda _i: self.changed.emit(self.seconds()))

    def seconds(self) -> float:
        return float(self.spin.value() * (self.unit.currentData() or 1))

    def set_seconds(self, seconds: float) -> None:
        """Shows the largest unit that keeps the number whole: 1800 s is 30 minutes."""
        s = max(0, int(round(seconds)))
        index = 0
        for i, (_name, factor) in enumerate(self.UNITS):
            if s and s % factor == 0:
                index = i
        blocked = self.spin.blockSignals(True), self.unit.blockSignals(True)
        self.unit.setCurrentIndex(index)
        self.spin.setValue(s // self.UNITS[index][1])
        self.spin.blockSignals(blocked[0])
        self.unit.blockSignals(blocked[1])
        self.changed.emit(self.seconds())


class CountOf(QWidget):
    """How many of a whole: [500] of 1,000 files. With a total of 0 it is disabled."""

    changed = Signal(int)

    def __init__(self, total: int = 0, noun: str = "items", value: int | None = None):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.spin = NoWheelSpinBox()
        self.spin.setFixedWidth(110)
        self.of = label("", "Note")
        lay.addWidget(self.spin)
        lay.addWidget(self.of)
        lay.addStretch()
        self.noun = noun
        self.set_total(total, value)
        self.spin.valueChanged.connect(self.changed.emit)

    def set_total(self, total: int, value: int | None = None) -> None:
        total = max(0, int(total))
        if total == 0:
            self.spin.setRange(0, 0)
            self.spin.setEnabled(False)
        else:
            self.spin.setEnabled(True)
            self.spin.setRange(1, total)
            self.spin.setValue(total if value is None else max(1, min(total, value)))
        self.of.setText(f"of {total:,} {self.noun}")

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, value: int) -> None:
        self.spin.setValue(value)


class RangeInput(QWidget):
    """[30] to [120] seconds. Raising the minimum past the maximum moves the maximum, and back."""

    changed = Signal(int, int)

    def __init__(self, low: int = 0, high: int = 0, unit: str = "seconds", maximum: int = 86_400):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.low = NoWheelSpinBox(0, maximum, low)
        self.high = NoWheelSpinBox(0, maximum, max(low, high))
        for spin in (self.low, self.high):
            spin.setFixedWidth(84)
        lay.addWidget(self.low)
        lay.addWidget(label("to", "Note"))
        lay.addWidget(self.high)
        lay.addWidget(label(unit, "Note"))
        lay.addStretch()
        self.low.valueChanged.connect(lambda v: (self.high.value() < v and self.high.setValue(v), self._emit()))
        self.high.valueChanged.connect(lambda v: (self.low.value() > v and self.low.setValue(v), self._emit()))

    def _emit(self) -> None:
        self.changed.emit(self.low.value(), self.high.value())

    def values(self) -> tuple[int, int]:
        return self.low.value(), self.high.value()


# ---------------------------------------------------------------------------
# Window: title bar, sidebar, pages
# ---------------------------------------------------------------------------
class TitleButton(QPushButton):
    """Minimize, maximize/restore or close, drawn with a 1.4px pen. Close turns red on hover."""

    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.setObjectName("TitleButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 32)
        self._hover = False
        self.set_kind(kind)

    def set_kind(self, kind: str) -> None:
        self.kind = kind
        self.setToolTip({"min": "Minimize", "max": "Maximize", "restore": "Restore",
                         "close": "Close"}.get(kind, ""))
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        is_close = self.kind == "close"
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(TOKENS["close"] if is_close else TOKENS["hover"]))
            p.drawRect(self.rect())
        p.setPen(_round_pen(TOKENS["text"] if self._hover else TOKENS["muted"], 1.4))
        p.setBrush(Qt.NoBrush)
        cx, cy = self.width() / 2, self.height() / 2
        if self.kind == "min":
            p.drawLine(QPointF(cx - 5, cy + 0.5), QPointF(cx + 5, cy + 0.5))
        elif self.kind == "max":
            p.drawRoundedRect(QRectF(cx - 5, cy - 5, 10, 10), 2, 2)
        elif self.kind == "restore":
            p.drawRoundedRect(QRectF(cx - 5, cy - 2, 7.5, 7.5), 1.5, 1.5)
            p.drawPolyline(_poly((cx - 2, cy - 2), (cx - 2, cy - 5), (cx + 5, cy - 5), (cx + 5, cy + 2),
                                 (cx + 2.5, cy + 2)))
        else:
            p.drawLine(QPointF(cx - 4.5, cy - 4.5), QPointF(cx + 4.5, cy + 4.5))
            p.drawLine(QPointF(cx + 4.5, cy - 4.5), QPointF(cx - 4.5, cy + 4.5))
        p.end()


class TitleBar(QWidget):
    """50px, draggable, double-click maximizes. Logo and name on the left, window buttons right."""

    def __init__(self, window: QMainWindow, title: str, mark: QPixmap | None = None):
        super().__init__(window)
        self.window_ = window
        self._drag_pos = None
        self.setObjectName("TitleBar")
        self.setFixedHeight(50)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(mark or app_mark(20))
        logo.setFixedSize(20, 20)
        lay.addWidget(logo)
        self.title = label(title, "TitleLabel")
        lay.addWidget(self.title)
        lay.addStretch()
        self.min_btn = TitleButton("min")
        self.min_btn.clicked.connect(lambda _=False: window.showMinimized())
        self.max_btn = TitleButton("max")
        self.max_btn.clicked.connect(lambda _=False: self._toggle_max())
        self.close_btn = TitleButton("close")
        self.close_btn.clicked.connect(lambda _=False: window.close())
        for b in (self.min_btn, self.max_btn, self.close_btn):
            lay.addWidget(b)

    def set_maximized(self, maximized: bool) -> None:
        self.max_btn.set_kind("restore" if maximized else "max")

    def _toggle_max(self) -> None:
        self.window_.showNormal() if self.window_.isMaximized() else self.window_.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = _global_pos(event) - self.window_.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if (self._drag_pos is not None and event.buttons() & Qt.LeftButton
                and not self.window_.isMaximized()):
            self.window_.move(_global_pos(event) - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_max()


class _InvisibleSizeGrip(QSizeGrip):
    def paintEvent(self, _event):
        pass


class QuietWindow(QMainWindow):
    """A frameless window: rounded frame with a shadow, title bar, a 216px sidebar (pages on top,
    Settings-like pages at the bottom, a status footer) and the pages on the right."""

    page_changed = Signal(int)
    MARGIN = 14

    def __init__(self, title: str, size: tuple[int, int] = (1140, 760),
                 min_size: tuple[int, int] = (980, 680), mark: QPixmap | None = None,
                 sidebar_width: int = 216):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(*min_size)
        self.resize(*size)
        self.setWindowIcon(QIcon(app_mark(64)))

        root = QWidget()
        self.setCentralWidget(root)
        self._root_layout = QVBoxLayout(root)
        m = self.MARGIN
        self._root_layout.setContentsMargins(m, m, m, m)

        self.frame = QFrame()
        self.frame.setObjectName("WindowFrame")
        self.frame.setProperty("maximized", False)
        self._root_layout.addWidget(self.frame)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 190))
        shadow.setOffset(0, 8)
        self.frame.setGraphicsEffect(shadow)

        fl = QVBoxLayout(self.frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)
        self.title_bar = TitleBar(self, title, mark)
        fl.addWidget(self.title_bar)
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        fl.addWidget(body, 1)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setProperty("maximized", False)
        self.sidebar.setFixedWidth(sidebar_width)
        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(12, 18, 12, 14)
        sl.setSpacing(2)
        self._top_nav = QVBoxLayout()
        self._top_nav.setSpacing(2)
        self._bottom_nav = QVBoxLayout()
        self._bottom_nav.setSpacing(2)
        sl.addLayout(self._top_nav)
        sl.addStretch()
        sl.addLayout(self._bottom_nav)
        sl.addSpacing(8)
        status = QFrame()
        status.setObjectName("SidebarStatus")
        st = QVBoxLayout(status)
        st.setContentsMargins(12, 10, 12, 10)
        st.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(8)
        self._status_dot = status_dot(TOKENS["faint"])
        top.addWidget(self._status_dot, 0, Qt.AlignVCenter)
        self._status_text = label("Idle", "SidebarStatusText")
        top.addWidget(self._status_text)
        top.addStretch()
        st.addLayout(top)
        self._footnote = label("", "SidebarVersion")
        self._footnote.hide()
        st.addWidget(self._footnote)
        sl.addWidget(status)
        bl.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("Content")
        self.stack.setProperty("maximized", False)
        bl.addWidget(self.stack, 1)
        self.nav_buttons: list[QPushButton] = []

        self.size_grip = _InvisibleSizeGrip(self.frame)
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.raise_()
        self.note = ErrorNote(self.frame)

    def add_page(self, name: str, icon_kind: str, widget: QWidget, bottom: bool = False) -> int:
        """Adds a page and its sidebar button; bottom=True puts the button above the status."""
        index = self.stack.addWidget(widget)
        btn = QPushButton(f"  {name}")
        btn.setObjectName("NavButton")
        btn.setIcon(icon(icon_kind))
        btn.setIconSize(QSize(18, 18))
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _=False, i=index: self.set_page(i))
        (self._bottom_nav if bottom else self._top_nav).addWidget(btn)
        self.nav_buttons.append(btn)
        if index == 0:
            btn.setChecked(True)
        return index

    def set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)
        self.page_changed.emit(index)

    def set_status(self, text: str, tone: str = "idle") -> None:
        """The sidebar footer: tone is idle (faint), good, warn or bad."""
        color = {"good": TOKENS["good"], "warn": TOKENS["warn"], "bad": TOKENS["bad"]}.get(tone, TOKENS["faint"])
        set_dot(self._status_dot, color)
        self._status_text.setText(text)

    def set_footnote(self, text: str, tooltip: str = "") -> None:
        """The faint line under the status, such as "My app v1.0 · settings.ini"."""
        self._footnote.setText(text)
        self._footnote.setToolTip(tooltip)
        self._footnote.setVisible(bool(text))

    def show_error(self, title: str, text: str, seconds: int = 20) -> None:
        self.note.show_message(title, text, seconds)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.size_grip.move(self.frame.width() - self.size_grip.width(),
                            self.frame.height() - self.size_grip.height())

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            maximized = self.isMaximized()
            for w in (self.frame, self.stack, self.sidebar):
                w.setProperty("maximized", maximized)
                repolish(w)
            m = 0 if maximized else self.MARGIN
            self._root_layout.setContentsMargins(m, m, m, m)
            self.size_grip.setVisible(not maximized)
            self.title_bar.set_maximized(maximized)
        super().changeEvent(event)


class Page(QWidget):
    """A page: a 26px title and a subtitle on the left, actions on the right, then `body`."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 26, 32, 26)
        outer.setSpacing(0)
        header = QHBoxLayout()
        header.setSpacing(8)
        tb = QVBoxLayout()
        tb.setSpacing(4)
        self.title = label(title, "PageTitle")
        self.subtitle = label(subtitle, "PageSubtitle", wrap=True)
        self.subtitle.setVisible(bool(subtitle))
        tb.addWidget(self.title)
        tb.addWidget(self.subtitle)
        header.addLayout(tb, 1)
        self.action_bar = QHBoxLayout()
        self.action_bar.setSpacing(8)
        header.addLayout(self.action_bar)
        outer.addLayout(header)
        outer.addSpacing(20)
        self.body = QVBoxLayout()
        self.body.setSpacing(0)
        outer.addLayout(self.body, 1)

    def add_action(self, widget: QWidget) -> QWidget:
        self.action_bar.addWidget(widget, 0, Qt.AlignVCenter)
        return widget


class CategoryView(QWidget):
    """Settings layout: a 160px category list on the left, a scrolling page per category."""

    def __init__(self, width: int = 160):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(28)
        nav = QWidget()
        nav.setFixedWidth(width)
        self._nav = QVBoxLayout(nav)
        self._nav.setContentsMargins(0, 0, 0, 0)
        self._nav.setSpacing(2)
        self._nav.addStretch()
        lay.addWidget(nav)
        self.pages = QStackedWidget()
        lay.addWidget(self.pages, 1)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QPushButton] = []

    def add(self, name: str, icon_kind: str, widgets: Sequence[QWidget]) -> int:
        """Adds a category whose page stacks `widgets` (usually SettingsSections)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("PageBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 12, 26)
        bl.setSpacing(10)
        for w in widgets:
            bl.addWidget(w)
        bl.addStretch()
        scroll.setWidget(body)
        index = self.pages.addWidget(scroll)
        b = QPushButton(f"  {name}")
        b.setObjectName("NavButton")
        b.setIcon(icon(icon_kind))
        b.setIconSize(QSize(16, 16))
        b.setCheckable(True)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, i=index: self.set_index(i))
        self.group.addButton(b, index)
        self._nav.insertWidget(self._nav.count() - 1, b)
        self.buttons.append(b)
        if index == 0:
            b.setChecked(True)
        return index

    def set_index(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.buttons[index].setChecked(True)


# ---------------------------------------------------------------------------
# Settings rows and save state
# ---------------------------------------------------------------------------
def setting_row(title: str, help_text: str = "", control: QWidget | None = None,
                stacked: bool = False, control_width: int = 340) -> QWidget:
    """Label and helper on the left, one control on the right (stacked: the control below).
    No box. The helper label is row.help, for set_state(row.help, "on"/"off")."""
    row = QWidget()
    row.setObjectName("SettingRow")
    lay = QVBoxLayout(row) if stacked else QHBoxLayout(row)
    lay.setContentsMargins(0, 14, 0, 14)
    lay.setSpacing(12 if stacked else 32)
    text = QWidget()
    tl = QVBoxLayout(text)
    tl.setContentsMargins(0, 0, 0, 0)
    tl.setSpacing(3)
    row.label = label(title, "RowLabel")
    tl.addWidget(row.label)
    row.help = label(help_text, "RowHelp", wrap=True)
    row.help.setVisible(bool(help_text))
    tl.addWidget(row.help)
    holder = QWidget()
    hl = QVBoxLayout(holder)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    if isinstance(control, ToggleSwitch):
        hl.addWidget(control, 0, Qt.AlignRight)
    elif control is not None:
        hl.addWidget(control)
    if stacked:
        lay.addWidget(text)
        lay.addWidget(holder)
    else:
        holder.setFixedWidth(control_width)
        lay.addWidget(text, 1, Qt.AlignVCenter)
        lay.addWidget(holder, 0, Qt.AlignVCenter)
    row.control = control
    return row


class SettingsSection(QFrame):
    """A heading (15px) and an optional faint subtitle, then rows with a 1px line between them."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("SettingsSection")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(0, 18, 0, 12)
        hl.setSpacing(3)
        hl.addWidget(label(title, "SettingsHeading"))
        if subtitle:
            hl.addWidget(label(subtitle, "SectionSub", wrap=True))
        self._lay.addWidget(head)

    def add_row(self, title: str, help_text: str = "", control: QWidget | None = None,
                stacked: bool = False, control_width: int = 340) -> QWidget:
        row = setting_row(title, help_text, control, stacked, control_width)
        self._lay.addWidget(Divider())
        self._lay.addWidget(row)
        return row


class SaveState(QPushButton):
    """The status next to Save: "Unsaved changes", "2 issues to review" (click: first issue) or
    "All changes saved" for about 2 s. Pass the Save button to have it disabled when clean."""

    issue_clicked = Signal(object)

    def __init__(self, save_button: QPushButton | None = None):
        super().__init__("")
        self.setObjectName("StatusButton")
        self.setFlat(True)
        self.save_button = save_button
        self._dirty = False
        self._issues: list = []
        self._flash = ""
        self.clicked.connect(lambda _=False: self._issues and self.issue_clicked.emit(self._issues[0]))
        self._update()

    def set_dirty(self, dirty: bool = True) -> None:
        self._dirty = bool(dirty)
        self._update()

    def set_issues(self, issues: Sequence) -> None:
        """Strings, or (key, message) pairs; issue_clicked gets the first one."""
        self._issues = list(issues)
        self._update()

    def flash_saved(self, ms: int = 2200) -> None:
        self._dirty = False
        self._flash = "All changes saved"
        self._update()
        QTimer.singleShot(ms, self._clear_flash)

    def _clear_flash(self) -> None:
        self._flash = ""
        self._update()

    def _update(self) -> None:
        tip = ""
        if self._flash:
            text, state = self._flash, "ok"
        elif self._issues:
            n = len(self._issues)
            text, state = f"{n} issue{'s' if n != 1 else ''} to review", "warn"
            tip = "\n".join("• " + (m[1] if isinstance(m, tuple) else str(m)) for m in self._issues)
        elif self._dirty:
            text, state = "Unsaved changes", "dirty"
        else:
            text, state = "", ""
        self.setText(text)
        self.setToolTip(tip)
        self.setVisible(bool(text))
        self.setCursor(Qt.PointingHandCursor if state == "warn" else Qt.ArrowCursor)
        set_state(self, state)
        if self.save_button is not None:
            self.save_button.setEnabled(self._dirty)
            self.save_button.setToolTip("" if self._dirty else "No changes to save")


# ---------------------------------------------------------------------------
# Live progress: stats, step track, item rows, item list, error note
# ---------------------------------------------------------------------------
class Stat(QFrame):
    """A flat stat: a status dot and a label above a 26px number."""

    def __init__(self, title: str, color: str | None = None, value="0"):
        super().__init__()
        self.setObjectName("Stat")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(status_dot(color or TOKENS["accent"]), 0, Qt.AlignVCenter)
        top.addWidget(label(title, "StatTitle"))
        top.addStretch()
        lay.addLayout(top)
        self.value = label(str(value), "StatNumber")
        lay.addWidget(self.value)

    def set_value(self, value) -> None:
        self.value.setText(f"{value:,}" if isinstance(value, int) else str(value))


def stats_row(stats: Sequence[Stat]) -> QHBoxLayout:
    """Stats 48px apart, no boxes."""
    row = QHBoxLayout()
    row.setSpacing(48)
    for s in stats:
        row.addWidget(s)
    row.addStretch()
    return row


class StepTrack(QWidget):
    """One 22x4 segment per step: done --good, current --text, failed --bad, to come --active."""

    SEG, GAP, H = 22, 4, 4

    def __init__(self):
        super().__init__()
        self.count, self.at, self.state = 1, 0, ""
        self.setFixedHeight(self.H + 2)
        self.setFixedWidth(self.SEG)

    def set(self, count: int, at: int, state: str = "") -> None:
        self.count, self.at, self.state = max(1, count), at, state
        self.setFixedWidth(self.count * self.SEG + (self.count - 1) * self.GAP)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        y = (self.height() - self.H) / 2
        for i in range(self.count):
            if self.state == "done" or i < self.at:
                color = TOKENS["good"]
            elif i == self.at and self.state == "failed":
                color = TOKENS["bad"]
            elif i == self.at:
                color = TOKENS["text"]
            else:
                color = TOKENS["active"]
            p.setBrush(QColor(color))
            p.drawRoundedRect(QRectF(i * (self.SEG + self.GAP), y, self.SEG, self.H), 2, 2)
        p.end()


class ItemRow(QWidget):
    """One item of a run: avatar, name, short id, what it is doing over a step track, the result."""

    AVATAR = 30
    RESULT_WIDTH = 210  # fixed, so the step tracks of all rows line up

    def __init__(self, name: str, sub: str = "", picture: bytes = b""):
        super().__init__()
        self.setObjectName("ItemRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 9, 4, 9)
        lay.setSpacing(12)
        self.avatar = QLabel()
        self.avatar.setFixedSize(self.AVATAR, self.AVATAR)
        lay.addWidget(self.avatar, 0, Qt.AlignVCenter)
        names = QVBoxLayout()
        names.setSpacing(1)
        self.name = label(name, "ItemName")
        self.sub = label(sub, "ItemSub")
        names.addWidget(self.name)
        names.addWidget(self.sub)
        lay.addLayout(names, 1)
        holder = QWidget()
        holder.setFixedWidth(150)
        pl = QVBoxLayout(holder)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(5)
        self.status = label("", "ItemStatus")
        self.track = StepTrack()
        pl.addWidget(self.status)
        pl.addWidget(self.track)
        lay.addWidget(holder, 0, Qt.AlignVCenter)
        self.result = label("", "ItemResult")
        self.result.setFixedWidth(self.RESULT_WIDTH)
        self.result.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.result, 0, Qt.AlignVCenter)
        self._picture = picture
        self._draw_avatar()

    def set_name(self, name: str, sub: str | None = None) -> None:
        self.name.setText(name)
        if sub is not None:
            self.sub.setText(sub)
        self._draw_avatar()

    def set_picture(self, data: bytes) -> None:
        self._picture = data
        self._draw_avatar()

    def _draw_avatar(self) -> None:
        self.avatar.setPixmap(round_pixmap(self._picture, self.name.text(), self.AVATAR))

    def set_progress(self, steps: Sequence[str], at: int, state: str = "running",
                     status: str | None = None, result: str | None = None,
                     result_tone: str | None = None) -> None:
        """steps: step names ("Read", "Upload", ...); at: the current step; state: running,
        waiting, done or failed. status and result default to plain words for the state."""
        steps = list(steps) or ["Done"]
        at = max(0, min(at, len(steps) - 1))
        self.track.set(len(steps), len(steps) if state == "done" else at, state)
        self.track.setToolTip("  →  ".join(steps))
        if status is None:
            status = {"done": "Done", "failed": f"Failed at {steps[at]}" if len(steps) > 1 else "Failed",
                      "waiting": "Waiting"}.get(state, f"{steps[at]}…")
        self.status.setText(status)
        set_state(self.status, {"done": "ok", "failed": "bad"}.get(state, ""))
        if result is None:
            result = {"done": "Done", "failed": "Failed"}.get(state, "")
        tone = result_tone if result_tone is not None else {"done": "ok", "failed": "bad"}.get(state, "")
        metrics = self.result.fontMetrics()
        self.result.setText(metrics.elidedText(result, Qt.ElideRight, self.RESULT_WIDTH))
        self.result.setToolTip(result if self.result.text() != result else "")
        set_state(self.result, tone)


class ItemList(QScrollArea):
    """The rows of a run, newest on top, a thin line between them, and an empty state."""

    def __init__(self, empty_text: str = "Items show here once you start a run."):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        body.setObjectName("PageBody")
        self._lay = QVBoxLayout(body)
        self._lay.setContentsMargins(16, 4, 16, 8)
        self._lay.setSpacing(0)
        self._empty = label(empty_text, "RowHelp")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setContentsMargins(0, 40, 0, 0)
        self._lay.addWidget(self._empty)
        self._lay.addStretch()
        self.setWidget(body)
        self.rows: list[ItemRow] = []

    def add(self, row: ItemRow) -> ItemRow:
        """Adds a row on top."""
        self._empty.hide()
        if self.rows:
            self._lay.insertWidget(1, Divider())
        self._lay.insertWidget(1, row)
        self.rows.append(row)
        return row

    def clear(self) -> None:
        for i in reversed(range(self._lay.count())):
            w = self._lay.itemAt(i).widget()
            if w is not None and w is not self._empty:
                w.setParent(None)
                w.deleteLater()
        self.rows.clear()
        self._empty.show()


class Chip(QWidget):
    """A found item in place of its field: round picture, name, a faint line, and a pencil."""

    edit_requested = Signal()
    AVATAR = 36

    def __init__(self):
        super().__init__()
        self.value = ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self.avatar = QLabel()
        self.avatar.setFixedSize(self.AVATAR, self.AVATAR)
        lay.addWidget(self.avatar, 0, Qt.AlignVCenter)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = label("", "ItemName")
        self.sub = label("", "ItemSub")
        text.addWidget(self.name)
        text.addWidget(self.sub)
        lay.addLayout(text, 1)
        self.edit = QPushButton()
        self.edit.setObjectName("GhostButton")
        self.edit.setIcon(icon("edit", TOKENS["muted"]))
        self.edit.setIconSize(QSize(16, 16))
        self.edit.setFixedSize(32, 32)
        self.edit.setCursor(Qt.PointingHandCursor)
        self.edit.setToolTip("Change")
        self.edit.clicked.connect(lambda _=False: self.edit_requested.emit())
        lay.addWidget(self.edit, 0, Qt.AlignVCenter)

    def set(self, value: str, name: str, sub: str = "", picture: bytes = b"", edit_tip: str = "Change") -> None:
        self.value = value
        self.name.setText(name)
        self.sub.setText(sub)
        self.edit.setToolTip(edit_tip)
        self.avatar.setPixmap(round_pixmap(picture, name, self.AVATAR, fg=TOKENS["text"]))


class LookupField(QWidget):
    """A line edit that turns into a Chip once its value is found. Connect `lookup` to start a
    lookup (600ms after typing stops), then call found() or not_found()."""

    lookup = Signal(str)

    def __init__(self, text: str = "", placeholder: str = ""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.chip = Chip()
        self.chip.hide()
        self.edit = QLineEdit(text)
        self.edit.setPlaceholderText(placeholder)
        self.message = label("", "BadText", wrap=True)
        self.message.hide()
        lay.addWidget(self.chip)
        lay.addWidget(self.edit)
        lay.addWidget(self.message)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(600)
        self._timer.timeout.connect(lambda: self.edit.text().strip() and self.lookup.emit(self.edit.text().strip()))
        self.edit.textChanged.connect(lambda _t: (self.message.hide(), self._timer.start()))
        self.edit.editingFinished.connect(self._end_edit)
        self.chip.edit_requested.connect(self._start_edit)

    def text(self) -> str:
        return self.edit.text().strip()

    def found(self, name: str, sub: str = "", picture: bytes = b"", edit_tip: str = "Change") -> None:
        self.chip.set(self.text(), name, sub, picture, edit_tip)
        self.message.hide()
        if not self.edit.hasFocus():
            self.edit.hide()
            self.chip.show()

    def not_found(self, text: str) -> None:
        self.chip.hide()
        self.edit.show()
        self.message.setText(text)
        self.message.show()

    def _start_edit(self) -> None:
        self.chip.hide()
        self.edit.show()
        self.edit.setFocus()
        self.edit.selectAll()

    def _end_edit(self) -> None:
        if self.chip.value and self.chip.value == self.text():
            self.edit.hide()
            self.chip.show()


class ErrorNote(QFrame):
    """An error in the bottom-right corner of its parent: red dot, title, selectable text, an
    optional action ("Logs") and a close button. It stays while the pointer is on it."""

    action_clicked = Signal()

    def __init__(self, parent: QWidget, action_text: str | None = "Logs", width: int = 440):
        super().__init__(parent)
        self.setObjectName("ErrorNote")
        self.setFixedWidth(width)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 8, 12)
        lay.setSpacing(10)
        dot_box = QVBoxLayout()
        dot_box.setContentsMargins(0, 5, 0, 0)
        dot_box.addWidget(status_dot(TOKENS["bad"]))
        dot_box.addStretch()
        lay.addLayout(dot_box)
        text = QVBoxLayout()
        text.setSpacing(3)
        self.title = label("", "NoteTitle")
        self.body = label("", "NoteText", wrap=True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.addWidget(self.title)
        text.addWidget(self.body)
        lay.addLayout(text, 1)
        self.action = button(action_text or "", "ghost", on_click=self.action_clicked.emit)
        self.action.setVisible(bool(action_text))
        lay.addWidget(self.action, 0, Qt.AlignTop)
        close = button("✕", "ghost", on_click=self.hide, tooltip="Close")
        lay.addWidget(close, 0, Qt.AlignTop)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._expire)
        parent.installEventFilter(self)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False

    def enterEvent(self, event):
        self._timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isVisible():
            self._timer.start(6000)
        super().leaveEvent(event)

    def _expire(self) -> None:
        if not self.underMouse():
            self.hide()

    def _place(self) -> None:
        p = self.parentWidget()
        lay = self.layout()
        lay.activate()
        height = lay.heightForWidth(self.width()) if lay.hasHeightForWidth() else self.sizeHint().height()
        self.resize(self.width(), max(height, self.minimumSizeHint().height()))
        self.move(max(0, p.width() - self.width() - 30), max(0, p.height() - self.height() - 30))

    def show_message(self, title: str, text: str, seconds: int = 20) -> None:
        self.title.setText(title)
        self.body.setText(text)
        self._place()
        self.show()
        self.raise_()
        self._timer.start(seconds * 1000)


# ---------------------------------------------------------------------------
# Stepped popup dialog
# ---------------------------------------------------------------------------
def form_grid(label_width: int = 92) -> QGridLayout:
    """The two-column grid of a dialog step: short muted labels on the left, controls right."""
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(14)
    grid.setColumnMinimumWidth(0, label_width)
    grid.setColumnStretch(2, 1)
    return grid


def form_label(text: str) -> QLabel:
    return label(text, "FormLabel")


def detail_grid(rows: Sequence[tuple[str, str, QWidget]], label_width: int = 170) -> QGridLayout:
    """Rows of a details step: a label with a helper line on the left, the control on the right."""
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(18)
    grid.setVerticalSpacing(16)
    grid.setColumnStretch(1, 1)
    grid.setColumnMinimumWidth(0, label_width)
    for r, (title, help_text, widget) in enumerate(rows):
        text = QWidget()
        tl = QVBoxLayout(text)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(1)
        tl.addWidget(label(title, "RowLabel"))
        if help_text:
            tl.addWidget(label(help_text, "RowHelp"))
        grid.addWidget(text, r, 0, Qt.AlignTop)
        grid.addWidget(widget, r, 1, Qt.AlignTop)
    grid.setRowStretch(len(rows), 1)
    return grid


def summary_block(eyebrow: str = "THIS RUN") -> tuple[QWidget, QLabel]:
    """A divider, a faint eyebrow and a sentence label: say what will happen. Returns (block, label)."""
    block = QWidget()
    lay = QVBoxLayout(block)
    lay.setContentsMargins(0, 22, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(Divider())
    lay.addSpacing(12)
    lay.addWidget(label(eyebrow, "Eyebrow"))
    lay.addSpacing(4)
    text = label("", "Summary", wrap=True)
    text.setTextFormat(Qt.RichText)
    lay.addWidget(text)
    return block, text


class StepDialog(QDialog):
    """A job set up in short steps, in a rounded frameless popup:

    header: title, a crumb of what was picked, close; left: the steps (210px); right: "Step N of M",
    title, subtitle and the step's page; footer: a message, Cancel, Back and the primary button
    ("Next", then `finish_text` on the last step). Steps already reached can be clicked to go back.
    Number keys pick options of an OptionList on the current step. Set `check` to a function
    (step index) -> str that returns why the step cannot go on, or "".
    """

    step_changed = Signal(int)

    def __init__(self, title: str, finish_text: str = "Done", parent: QWidget | None = None,
                 width: int = 820):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(width)
        self.finish_text = finish_text
        self.check: Callable[[int], str] | None = None
        self.step = 0
        self._steps: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("DialogFrame")
        root.addWidget(frame)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 10, 10, 10)
        hl.addWidget(label(title, "DialogHeaderTitle"))
        hl.addSpacing(10)
        self.crumb = label("", "DialogCrumb")
        hl.addWidget(self.crumb)
        hl.addStretch()
        close = TitleButton("close")
        close.setFixedSize(34, 30)
        close.clicked.connect(self.reject)
        hl.addWidget(close)
        fl.addWidget(header)
        fl.addWidget(Divider())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        fl.addLayout(body, 1)
        nav = QWidget()
        nav.setObjectName("DialogNav")
        nav.setFixedWidth(210)
        self._nav = QVBoxLayout(nav)
        self._nav.setContentsMargins(12, 14, 12, 14)
        self._nav.setSpacing(2)
        self._nav.addStretch()
        body.addWidget(nav)
        body.addWidget(Divider(vertical=True))

        right = QWidget()
        body.addWidget(right, 1)
        lay = QVBoxLayout(right)
        lay.setContentsMargins(28, 20, 28, 18)
        lay.setSpacing(0)
        self.step_label = label("", "StepText")
        lay.addWidget(self.step_label)
        lay.addSpacing(4)
        self.title = label("", "PageTitle")
        lay.addWidget(self.title)
        self.subtitle = label("", "PageSubtitle", wrap=True)
        lay.addWidget(self.subtitle)
        lay.addSpacing(16)
        self.pages = QStackedWidget()
        lay.addWidget(self.pages, 1)
        lay.addSpacing(14)
        lay.addWidget(Divider())
        lay.addSpacing(12)
        footer = QHBoxLayout()
        self.message = label("", "DialogMessage", wrap=True)
        footer.addWidget(self.message, 1)
        self.cancel_btn = button("Cancel", "ghost", on_click=self.reject)
        self.back_btn = button("Back", "ghost", on_click=lambda: self.go(-1))
        self.next_btn = button("Next", "primary", on_click=lambda: self.go(+1))
        self.next_btn.setDefault(True)
        for b in (self.cancel_btn, self.back_btn, self.next_btn):
            footer.addWidget(b)
        lay.addLayout(footer)

    def add_step(self, name: str, page: QWidget, title: str | None = None, subtitle: str = "",
                 icon_kind: str = "sliders") -> int:
        index = self.pages.addWidget(page)
        b = QPushButton(f"  {name}")
        b.setObjectName("NavButton")
        b.setIcon(icon(icon_kind))
        b.setIconSize(QSize(16, 16))
        b.setCheckable(True)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, i=index: self.jump(i))
        self._nav.insertWidget(self._nav.count() - 1, b)
        self._steps.append({"button": b, "title": title or name, "subtitle": subtitle, "visible": True})
        self._update()
        return index

    def set_crumb(self, text: str) -> None:
        """What was picked so far, next to the title: "Saved files → Upload"."""
        self.crumb.setText(text)

    def set_message(self, text: str, tone: str = "") -> None:
        """The footer message; tone "bad" for a problem, "good" for a confirmation."""
        self.message.setText(text)
        set_state(self.message, tone)

    def set_subtitle(self, index: int, text: str) -> None:
        self._steps[index]["subtitle"] = text
        self._update()

    def set_step_visible(self, index: int, visible: bool) -> None:
        self._steps[index]["visible"] = visible
        self._update()

    def _visible(self) -> list[int]:
        return [i for i, s in enumerate(self._steps) if s["visible"]]

    def go(self, direction: int) -> None:
        steps = self._visible()
        if not steps:
            return
        at = steps.index(self.step) if self.step in steps else 0
        if direction > 0:
            problem = self.check(self.step) if self.check else ""
            if problem:
                self.set_message(problem, "bad")
                return
            if at == len(steps) - 1:
                self.accept()
                return
            self.step = steps[at + 1]
        elif at > 0:
            self.step = steps[at - 1]
        self.set_message("")
        self._update()

    def jump(self, index: int) -> None:
        """A step in the list: going back is always allowed, forward only with Next."""
        if index in self._visible() and index < self.step:
            self.step = index
            self.set_message("")
        self._update()

    def _update(self) -> None:
        steps = self._visible()
        if not steps:
            return
        if self.step not in steps:
            self.step = steps[-1]
        at = steps.index(self.step)
        for i, s in enumerate(self._steps):
            s["button"].setVisible(s["visible"])
            s["button"].setChecked(i == self.step)
            s["button"].setEnabled(i <= self.step)
        if self.pages.currentIndex() != self.step:
            # Focus stays on the primary button (Enter goes on) instead of falling into the
            # first field of the new step and selecting its text.
            self.next_btn.setFocus()
            self.pages.setCurrentIndex(self.step)
        self.step_label.setText(f"Step {at + 1} of {len(steps)}")
        self.title.setText(self._steps[self.step]["title"])
        self.subtitle.setText(self._steps[self.step]["subtitle"])
        self.subtitle.setVisible(bool(self._steps[self.step]["subtitle"]))
        self.back_btn.setVisible(at > 0)
        self.next_btn.setText(self.finish_text if at == len(steps) - 1 else "Next")
        self.step_changed.emit(self.step)

    def keyPressEvent(self, event):
        key = _iv(event.key())
        if _iv(Qt.Key_1) <= key <= _iv(Qt.Key_9):
            options = self.pages.currentWidget().findChild(OptionList)
            if options is not None:
                options.set_index(key - _iv(Qt.Key_1))
                return
        super().keyPressEvent(event)
