"""quit_designer: the part inside Designer. The server ends the process if this doesn't."""

from .core import _PM, cast, os


def quit_designer(agent_pid: int, closed_line: str) -> None:
    """Close Designer's windows once the bridge has sent this call's reply: the plugin runs what a job hands its
    `_after_reply` then, on the main thread (REVIEW.md SRV-151: 300 ms after the call returned, a time). A plugin
    installed before it, until Designer restarts, has none: 300 ms after, as before. Unsaved packages are
    unloaded first, so Designer doesn't stop at a save prompt. The server asks this of the Designer an agent started, but
    the request goes to whichever holds the port, so any other process refuses (REVIEW.md SRV-73). Once every window it
    closed has closed, `closed_line` goes into Designer's log, readable while its shutdown runs (measured, with the main
    thread blocked too): a server forcing the process tells its own shutdown hanging from a close that didn't take
    (REVIEW.md SRV-106). The windows it closed: those shown when it runs, Designer's own among them (REVIEW.md
    HLP-104), and, closed once too, those shown as they closed, a prompt that accepts its close not keeping Designer
    alive (REVIEW.md HLP-102) and one that refuses it keeping it (REVIEW.md HLP-105). It judges when it runs,
    before Designer's own quit decides, so its line can be wrong (REVIEW.md HLP-106; the limit stated, not worked
    around: DECISIONS.md, Bridge and quitting): a window refusing its close that shows after it judged (from a timer,
    measured) keeps Designer open after `closed_line`, and a dialog of Designer's window refusing its close is counted
    still open though Designer quits (measured). Its print goes to sys.stdout when
    it runs: a job of another client running then would take it into its own output (two clients on one port;
    sys.__stdout__ doesn't reach Designer's log, and `logging` lands there as an error: measured, REVIEW.md HLP-103)."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QStackedWidget

    if os.getpid() != agent_pid:
        raise RuntimeError(
            'this is Designer %d, not %d, the one an agent started: nothing closed' % (os.getpid(), agent_pid)
        )
    for p in [p for p in _PM.getUserPackages() if p.isModified()]:
        print('discarding unsaved changes:', p.getFilePath() or 'never-saved package')
        _PM.unloadUserPackage(p)
    qt_app = cast(QApplication, QApplication.instance())  # Designer's own: always there

    def close_windows() -> None:
        shown = [w for w in qt_app.topLevelWidgets() if w.isVisible()]
        for w in shown:
            w.close()
        # one shown as those closed (a prompt) is closed too, once (REVIEW.md HLP-105)
        since = [w for w in qt_app.topLevelWidgets() if w.isVisible() and w not in shown]
        for w in since:
            w.close()
        closed = shown + since
        still = [w for w in closed if w.isVisible()]
        # Designer quits on its own window, the visible QStackedWidget (REVIEW.md HLP-19, HLP-104); a window refusing its
        # close keeps it from quitting, one shown as Designer's closes too (measured), but not a dialog of Designer's
        # window (REVIEW.md HLP-106)
        if not any(isinstance(w, QStackedWidget) for w in shown):
            print("quit: Designer's own window wasn't shown: %d other window(s) closed" % len(closed))
        elif still:
            print('quit: %d of the %d window(s) it closed still open' % (len(still), len(closed)))
        else:
            print(closed_line)

    after_reply = globals().get('_after_reply')  # the plugin's, in the job's scope
    if after_reply is not None:
        after_reply(close_windows)
    else:
        QTimer.singleShot(300, close_windows)  # an older plugin's: no reply sent to wait for
    print('closing Designer')
