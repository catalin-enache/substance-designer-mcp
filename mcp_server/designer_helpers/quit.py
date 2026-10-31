"""quit_designer and its fallback."""

from .core import _PM, cast, os


def quit_designer(discard_unsaved: bool = False) -> None:
    """Close Designer's main window shortly after this call returns. Refuses while user packages
    have unsaved changes, unless discard_unsaved (then those packages are unloaded first, so
    Designer doesn't stop at a save prompt)."""
    from PySide6.QtCore import QTimer

    modified = [p for p in _PM.getUserPackages() if p.isModified()]
    if modified and not discard_unsaved:
        raise RuntimeError(
            'unsaved changes in %d package(s): %s. Save them (save_package) or pass '
            'discard_unsaved=True.'
            % (
                len(modified),
                '; '.join(
                    '%s [%s]'
                    % (
                        p.getFilePath() or 'never saved',
                        ', '.join(r.getIdentifier() for r in p.getChildrenResources(False)),
                    )
                    for p in modified
                ),
            )
        )
    for p in modified:
        print('discarding unsaved changes:', p.getFilePath() or 'never-saved package')
        _PM.unloadUserPackage(p)
    from PySide6.QtWidgets import QApplication

    qt_app = cast(QApplication, QApplication.instance())  # Designer's own: always there
    # getMainWindow() is a hidden QMainWindow; the window the user sees is another top-level
    # widget. Close the visible ones (Designer's normal shutdown). Fallback when a window refuses
    # to close: os._exit(), which ends the process without tearing Designer down. quit() would
    # not stop it (Qt 6 cancels it when a window refuses to close), and exit() runs the teardown
    # while Designer's own background threads still work: twice its licence check thread crashed
    # on objects already destroyed (REVIEW.md PLG-8). Until about 35 s after the quit the fallback
    # fires only while a window is still open and the normal shutdown hasn't begun, so a slow
    # shutdown isn't cut off (REVIEW.md HLP-12); after that it forces a Designer still running (see
    # below, REVIEW.md HLP-28). Deferred, so the bridge can still reply.
    # The shutdown has begun once every window accepted its Close (none visible after
    # close_windows). While it has, or while a close() is still running (a slow close handler,
    # REVIEW.md HLP-17), the fallback only looks again every second; about 35 s after the quit, a
    # window still visible (a stuck handler, REVIEW.md HLP-19), or a Designer still running with
    # every window closed (REVIEW.md HLP-23), is forced. A window that refuses to close is forced at 5 s. aboutToQuit isn't used:
    # its slots run in connection order, so it can't be relied on (REVIEW.md TST-19, TST-23).
    import time

    closed_all: list[bool] = []
    closing: list[bool] = []
    give_up = time.monotonic() + 35

    def close_windows() -> None:
        closing.append(True)
        try:
            for w in qt_app.topLevelWidgets():
                if w.isVisible():
                    w.close()
        finally:
            closing.clear()
        if not any(w.isVisible() for w in qt_app.topLevelWidgets()):
            closed_all.append(True)

    def fallback() -> None:
        if (closing or closed_all) and time.monotonic() < give_up:
            QTimer.singleShot(1000, fallback)
            return
        # A timer can fire here only while Designer's event loop still runs, so with every window
        # closed it never went on to quit: force it rather than leave it running without a window
        # (REVIEW.md HLP-23)
        if closed_all or any(w.isVisible() for w in qt_app.topLevelWidgets()):
            os._exit(0)

    QTimer.singleShot(300, close_windows)
    QTimer.singleShot(5000, fallback)
    print('closing Designer')
