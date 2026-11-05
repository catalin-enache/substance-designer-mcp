"""quit_designer: the part inside Designer. The server ends the process if this doesn't."""

from .core import _PM, cast, os


def quit_designer(agent_pid: int) -> None:
    """Close Designer's windows shortly after this call returns, so the bridge can still reply. Unsaved packages are
    unloaded first, so Designer doesn't stop at a save prompt. The server asks this of the Designer an agent started, but
    the request goes to whichever holds the port, so any other process refuses (REVIEW.md SRV-73)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    if os.getpid() != agent_pid:
        raise RuntimeError(
            'this is Designer %d, not %d, the one an agent started: nothing closed' % (os.getpid(), agent_pid)
        )
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
