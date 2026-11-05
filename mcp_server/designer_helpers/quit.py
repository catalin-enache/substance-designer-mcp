"""quit_designer: the part inside Designer. The server ends the process if this doesn't."""

from .core import _PM, cast


def quit_designer() -> None:
    """Close Designer's windows shortly after this call returns, so the bridge can still reply. Unsaved packages are
    unloaded first, so Designer doesn't stop at a save prompt: the server only asks this of a Designer an agent started."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    for p in [p for p in _PM.getUserPackages() if p.isModified()]:
        print('discarding unsaved changes:', p.getFilePath() or 'never-saved package')
        _PM.unloadUserPackage(p)
    qt_app = cast(QApplication, QApplication.instance())  # Designer's own: always there

    def close_windows() -> None:
        for w in qt_app.topLevelWidgets():
            if w.isVisible():
                w.close()

    QTimer.singleShot(300, close_windows)
    print('closing Designer')
