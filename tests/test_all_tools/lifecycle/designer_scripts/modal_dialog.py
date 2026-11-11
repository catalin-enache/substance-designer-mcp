"""Runs inside Designer: opens a modal dialog from the event loop, for quit_designer to close Designer past it."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox

QTimer.singleShot(
    0,
    lambda: QMessageBox.information(
        None, 'sd_mcp self-test', 'A modal dialog; quit_designer must still close Designer.'
    ),
)
