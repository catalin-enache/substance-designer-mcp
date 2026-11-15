"""screenshot_designer('3d') in Designer (shoot_3d): the set-up checked, Designer's window put on screen, transparent,
and kept there until the render is read, the 3D view set up (view3d.py), and a render that may not have followed the
set-up said (REVIEW.md SRV-146, HLP-124).

Measured on macOS in a Designer an agent started (2026-11-13 and 2026-11-14), by panning the view with the helpers' own
drag and comparing its renders. The self-test's editor_panels_and_fit re-measures the first point (a window of
Designer's own covering it) and the second, but for its time, the identical render and the window never shown. It also
re-measures drags reaching the camera off screen, the top-level window and the page as macOS minimizes it, and the
last point. The rest was measured once.

- The 3D view's render (Copy Render to Clipboard) is the last frame the view drew while Designer's main window isn't
  on screen: minimized, fully covered by another window (Designer's own or another app's), or Designer hidden. A
  window partly covered draws. Drags given meanwhile reach the camera: the view shows them once it draws again, within
  0.25 s of the window coming on screen.
- A window made transparent (alphaValue 0) and brought in front is on screen for macOS and exposed for Qt within
  0.01 s, and the view draws: a pan changed the render, whether the window had been covered, minimized or Designer
  hidden. Its render was pixel-identical to one of the same view on screen (2026-11-14). Transparent alone, it still
  takes a click at its middle, as macOS says (NSWindow's windowNumberAtPoint, no click made). Click-through too
  (ignoresMouseEvents), the click reaches the window under it, so the shot makes it both. A window whole under it,
  one macOS had shown, stays visible for macOS (occlusionState) while it is transparent in front, and is covered once
  it is opaque again. A window made under it and never shown read covered either way, which a first probe took for
  the fact (REVIEW.md HLP-141).
- getMainWindow() is a page of the top-level window (GUIDE.md). When macOS minimizes the window, as its minimize button
  does, the top-level's isMinimized() is True and its showNormal() restores the window; the page's isMinimized() stays
  False, and its own showNormal() does nothing. The page minimized by Qt itself (showMinimized()) stops the drawing
  too, though still exposed. Forcing a redraw (update(), repaint(), requestUpdate(), an expose event) drew no frame.
- So macOS is asked (_MacWindow, mac_window.py): the window's isMiniaturized and occlusionState, the app's isHidden.
  orderFrontRegardless brings the window in front, un-minimized too, without making Designer the active app: the app
  in front kept it. unhideWithoutActivation shows a hidden Designer the same way. The window was exposed about 0.3 s
  after either. macOS says a window is covered 0.04 to 0.07 s after it is, idle and under load. A window minimized
  both by macOS and by Qt came back the same way, Qt's restore first, Designer still not active.
- A hidden Designer shown again that way, its windows transparent and its main window ordered in front, sometimes
  wasn't drawn: 0.5 s on, Designer was no longer hidden and CoreGraphics listed the window on screen, but macOS still
  counted it covered (occlusionState), so Qt never exposed it. That happened in 3 of 14 runs of the self-test's
  focus check, each in a Designer just started. Ordered in front again then, it was exposed within 0.06 s, 3 of 3
  (2026-11-14, REVIEW.md HLP-145). The same steps run alone never did it, in 33 tries: what sets it off isn't known.
- Two renders of an unchanged view are identical, pixel for pixel. A pan, an orbit or a zoom changes the render, and
  so does another mesh: Plane and Plane (hi-res), from the top, differ by 0.005 grey levels on average.
- The 3D view's Scene menu checks the mesh it shows (_mesh_shown).

Only the main window is looked at: a 3D View panel floating in a window of its own wasn't measured. Elsewhere than
macOS nothing was measured: the window is left as it is, and the shot taken as before.
"""

import contextlib
from collections.abc import Iterator

from .core import _APP, Any, Callable, cast
from .editor import _process_events
from .mac_window import _mac_window, _MacWindow
from .screenshots import _3d_dock, _3d_render
from .view3d import MESHES, _3d_set_up, _menu_action, _settle

ON_SCREEN_WAIT = 3.0  # s for Designer's window to be on screen once shown: about 0.3 s measured
SHOW_AGAIN = 0.5  # s after which a window still not on screen is put in front again, once (REVIEW.md HLP-145)
DRAW_WAIT = 0.5  # s for the 3D view to draw once on screen, and between renders taken again: within 0.25 s measured
RETAKES = 3  # renders taken again while identical to the one before a set-up that moved the camera or switched the mesh
WINDOW = "Designer's window: "
STALE = (
    '3D render: identical to the render before the set-up, though the set-up moved the camera or switched the mesh. '
    'The 3D view may not have been drawn. Shoot again with no set-up before judging it: pan, orbit and zoom move the '
    'camera from where it is. With no mesh in view, a pan or zoom changes nothing'
)
TRANSPARENT = (0.0, True)  # a window's opacity, and whether the mouse goes through it (_MacWindow.appearance)
OPAQUE = (1.0, False)
# what is done to bring the window on screen, said at the start of the shot and when it went off screen during it
BROUGHT = {
    'minimized': (
        "shown, transparent and without taking focus, as its 3D view isn't drawn while minimized",
        'shown again, transparent, as it was minimized during the shot',
    ),
    'hidden': (
        "shown, transparent and without taking focus, as its 3D view isn't drawn while Designer is hidden",
        'shown again, transparent, as Designer was hidden during the shot',
    ),
    'covered': (
        "brought in front, transparent and without taking focus, as its 3D view isn't drawn while covered",
        'brought in front again, transparent, as another window covered it during the shot',
    ),
}
# the page minimized by Qt (no user does that), restored by Qt in a window macOS shows
QT_RESTORED = (
    "un-minimized, as its 3D view isn't drawn while minimized; it stays so",
    'un-minimized again, as it was minimized during the shot; it stays so',
)


def _wait_on_screen(mw: Any, show: Callable[[], None]) -> None:  # Any: a Qt widget (screenshots.py)
    """Waits for Designer's main window to be on screen (exposed), then for the 3D view to draw (DRAW_WAIT); refused
    after ON_SCREEN_WAIT. A window still not exposed after SHOW_AGAIN is put in front again (`show`), once: macOS
    sometimes still counted it covered until then (the module docstring)."""
    step = 0.05
    for i in range(round(ON_SCREEN_WAIT / step)):
        if mw.windowHandle().isExposed():
            _settle(DRAW_WAIT)
            return
        if i == round(SHOW_AGAIN / step):
            show()
        _settle(step)
    raise RuntimeError(
        "the 3D view isn't drawn: Designer's window isn't on screen %g s after it was shown; ask the user to show it"
        % ON_SCREEN_WAIT
    )


class _Screen:
    """Designer's main window kept on screen through a 3D shot (_on_screen), transparent and click-through, so the user
    sees none of it and clicks the window under it (the user's choice: DECISIONS.md). The Explorer's menu, which
    graph= opens, is made transparent as it opens, and on macOS click-through too (view3d.py). On macOS only, each
    change said in a line ("Designer's window: ..."), without making Designer the active app:

    - a minimized window is shown, then minimized again;
    - a window covered by other windows is brought in front, then put back right behind the windows that were in
      front of it (REVIEW.md HLP-126): behind the one of them still on screen nearest the back. They are the normal
      windows in front of it each time it is brought in front: the user may raise one of them, or cover it again,
      during the shot (REVIEW.md HLP-131, HLP-139). It is left in front when none of them is still on screen, or none
      was found: put behind one off screen, or at the back, it would go behind every window (REVIEW.md HLP-130);
    - a hidden Designer is shown, every window of its own transparent, since all come back, then hidden again;
    - a page Qt minimized (no user does it) is restored by Qt, in a window macOS shows, and stays so. Its window is
      brought in front too, opaque, and left there: restored by Qt alone, the view drew no new frame.

    Each window is made opaque and clickable again once the window is back, minimized or hidden ones once off screen:
    before, the user would see them. again() looks before each render: a window the user covered, minimized or hid
    during the shot is put on screen the same way (REVIEW.md HLP-124). A Designer the user made the active app during
    the shot is left on screen, opaque (REVIEW.md HLP-125). It is made opaque at once, by between() before each
    set-up step and render: left transparent, the user would see no window, and a click would go through it to the app
    under it (REVIEW.md HLP-136). While Designer is that app, a window put on screen again isn't made transparent. A
    Designer the active app as the shot began counts as made the active app once the user comes back to it, if a
    look before a step or render saw them gone (REVIEW.md HLP-138). Refused when the window still isn't on screen
    after ON_SCREEN_WAIT."""

    def __init__(self, mw: Any, mac: _MacWindow | None) -> None:  # Any: a Qt widget (screenshots.py)
        self._mw = mw
        self._mac = mac
        self._was_active = mac is not None and mac.active()
        self._hidden = False  # Designer was shown: hidden again after
        self._minimized = False  # the window was shown: minimized again after
        self._covered = False  # the window was brought in front: put back after
        self._covers: list[int] = []  # the numbers of the windows found in front of it, each time it was brought
        self._faded: dict[int, tuple[float, bool]] = {}  # windows made transparent, held, and how each looked before

    def opaque_first(self) -> None:
        """Makes the window opaque and clickable again, saying so, if an earlier shot left it transparent. None should
        (_on_screen's handler), but the user would take a window left so for Designer gone."""
        mac = self._mac
        if mac is None:
            return
        window = mac.windows(every=False)[0]
        if mac.appearance(window) != OPAQUE:
            mac.set_appearance(window, *OPAQUE)
            print(WINDOW + 'made opaque again, as an earlier shot left it transparent')

    def _fade(self, every: bool) -> None:
        """Makes the window, or with `every` each window of Designer's, transparent and click-through (TRANSPARENT),
        once: each held first (a window closed meanwhile stays safe to message), then how it looked recorded, then
        changed. An abort between the hold and the record leaves a hold never ended: a leak, never a hold ended
        twice."""
        mac = cast(_MacWindow, self._mac)
        for window in mac.windows(every):
            if window not in self._faded:
                mac.hold(window)
                self._faded[window] = mac.appearance(window)
                mac.set_appearance(window, *TRANSPARENT)

    def unfade(self) -> None:
        """Gives each window made transparent its look back, and ends its hold. Run again after an abort, it does what
        is left, and never ends a hold twice; an abort between a record's removal and its hold's end leaks the hold."""
        mac = self._mac
        if mac is None:
            return
        for window, look in list(self._faded.items()):
            mac.set_appearance(window, *look)
            del self._faded[window]
            mac.let_go(window)

    def _taken_up(self) -> bool:
        """Whether the user made Designer the active app during the shot: it is, and wasn't as the shot began or at a
        look since (between)."""
        return self._mac is not None and self._mac.active() and not self._was_active

    def between(self) -> None:
        """Before each set-up step and render: once the user made Designer the active app during the shot, gives each
        window made transparent its look back at once, saying so (the class docstring)."""
        if self._mac is None:
            return
        if self._was_active and not self._mac.active():  # the user left it: coming back is a switch (REVIEW.md HLP-138)
            self._was_active = False
        if self._faded and self._taken_up():
            self.unfade()
            print(WINDOW + 'made opaque at once, as Designer became the active app during the shot')

    def _bring(self, again: bool) -> None:
        """Puts the window on screen, transparent, if it isn't, saying so: the first time, or `again` during the
        shot."""
        from PySide6 import QtCore

        mac = self._mac
        if mac is None:
            return
        # Designer's renderer follows the page's Qt state, which macOS minimizing doesn't change
        qt = self._mw.isMinimized()
        if qt:
            print(WINDOW + QT_RESTORED[again])
            self._mw.setWindowState(self._mw.windowState() & ~QtCore.Qt.WindowState.WindowMinimized)
        minimized = mac.minimized()
        hidden = mac.hidden()
        covered = not minimized and not hidden and mac.covered()
        if minimized or hidden or covered:
            way = 'minimized' if minimized else 'hidden' if hidden else 'covered'
            fade = not self._taken_up()  # the user, in Designer, sees it brought back (REVIEW.md HLP-136)
            print(WINDOW + (BROUGHT[way][again] if fade else BROUGHT[way][again].replace(', transparent', '')))
            if covered:
                # read before the record: an abort landing in it leaves nothing to put back (REVIEW.md HLP-130)
                found = mac.in_front()
                self._covers += [window for window in found if window not in self._covers]
                self._covered = True
            self._minimized = self._minimized or minimized
            self._hidden = self._hidden or hidden
            if fade:
                self._fade(every=hidden)  # shown again, a hidden Designer shows all its windows
            if hidden:
                mac.unhide()
            mac.show()
        elif qt:  # restored by Qt alone, the view drew no new frame; brought in front too, it drew (2026-11-14)
            mac.show()
        if qt or minimized or hidden or covered:
            _wait_on_screen(self._mw, mac.show)

    def again(self) -> None:
        """Before a render: makes the windows opaque once the user made Designer the active app (between), then puts
        the window on screen again if it went off screen during the shot."""
        self.between()
        self._bring(again=True)

    def _wait_off_screen(self) -> None:
        """Waits, at most ON_SCREEN_WAIT, for the window to be off screen once minimized or hidden again."""
        mac = cast(_MacWindow, self._mac)
        number = mac.number()
        step = 0.05
        for _ in range(round(ON_SCREEN_WAIT / step)):
            if not mac.on_screen(number):
                return
            _settle(step)

    def put_back(self) -> None:
        """Puts the window back as it was found off screen: minimized again, behind the windows that were in front of
        it, Designer hidden again. Leaves it on screen when the user made Designer the active app meanwhile, and in
        front when none of the windows that were in front of it is still on screen, or none was found. Then makes each
        window opaque and clickable again (unfade), a minimized or hidden one once off screen."""
        mac = self._mac
        if mac is None:
            return
        try:
            if not (self._hidden or self._minimized or self._covered):
                return
            if mac.active() and not self._was_active:
                print(WINDOW + 'left on screen, as Designer became the active app during the shot')
                return
            behind = mac.lowest(self._covers) if self._covered and not self._minimized else None
            if self._minimized:
                mac.minimize()
                print(WINDOW + 'minimized again')
            elif behind is not None:
                mac.put_below(behind)
                print(WINDOW + 'put back behind the window that was in front of it')
            elif self._covered and self._covers:
                print(WINDOW + 'left in front, as the window that was in front of it is no longer on screen')
            elif self._covered:
                print(WINDOW + 'left in front, as no window was found in front of it')
            if self._hidden:
                mac.hide()
                print(WINDOW + 'hidden again')
            if self._minimized or self._hidden:
                self._wait_off_screen()  # made opaque before, the user would see it
        finally:
            self.unfade()


@contextlib.contextmanager
def _on_screen(mw: Any) -> Iterator[_Screen]:  # Any: a Qt widget (screenshots.py: Qt widgets are Any in signatures)
    """Designer's main window on screen while the 3D view is set up and rendered (_Screen): put there now, and again
    before each render (_Screen.again). Off screen, the render is the view's last frame (the module docstring). The
    window is put back when the shot fails too. An abort landing on that step leaves the window on screen, opaque."""
    screen = _Screen(mw, _mac_window(mw))
    try:
        try:
            screen.opaque_first()
            screen._bring(again=False)
            yield screen
        finally:
            screen.put_back()
    except BaseException:
        # an abort fires once, so this handler runs untraced (the plugin's _make_tracer). put_back's own finally gives
        # the windows their look back after an abort in its body; this does it after one landing before that try or
        # inside unfade, and finishes opaque_first's change, which nothing records (REVIEW.md HLP-135)
        screen.unfade()
        screen.opaque_first()
        raise


def _mesh_shown(mw: Any, keep: list[object]) -> str | None:  # Any: a Qt widget (screenshots.py)
    """The mesh the 3D view shows: the one checked in its Scene menu (MESHES); None if none is."""
    from PySide6 import QtWidgets

    bar = _3d_dock(mw).findChildren(QtWidgets.QMenuBar)[0]
    keep.append(bar)
    menu = _menu_action(bar, keep, 'Scene').menu()
    keep.append(menu)
    menu.aboutToShow.emit()
    _process_events()
    names = [cast(str, a.text().replace('&', '')) for a in menu.actions() if a.isChecked()]
    shown = [name for name in names if name in MESHES]
    return shown[0] if shown else None


def shoot_3d(
    out_path: str,
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
    orbit: list[float] | None = None,
    pan: list[float] | None = None,
) -> None:
    """screenshot_designer('3d'): the 3D view set up when anything is given (_3d_set_up, set_3d_view's steps), then its
    render saved to `out_path`, with Designer's window on screen throughout (_on_screen, looked at again before each
    render). What _3d_set_up checks, and a 3D View panel not shown, is refused first, before the window changes
    (REVIEW.md HLP-127). What the steps find as they go is refused after, the window's lines in the error: with mesh=
    and tiling=, the new mesh's material; with graph=, its row in the Explorer. After a set-up that moved the camera (orbit, pan, zoom) or switched the mesh, a render
    identical to the one before it is taken again, at most RETAKES times DRAW_WAIT apart, then said (STALE): the view
    may not have been drawn. A view or a graph may already be what is shown, so they are no sign."""
    from PySide6 import QtGui

    given = bool(graph or mesh or view or zoom or tiling is not None or orbit or pan)
    set_up = _3d_set_up(graph, mesh, view, zoom, tiling, orbit, pan) if given else None
    mw = _APP.getQtForPythonUIMgr().getMainWindow()  # type: ignore[no-untyped-call]  # sd: no annotations
    keep: list[object] = [mw, _3d_dock(mw)]
    moving = bool(orbit or pan or zoom) or (mesh is not None and mesh != _mesh_shown(mw, keep))
    with _on_screen(mw) as screen:

        def render() -> QtGui.QImage:
            screen.again()
            shot: QtGui.QImage = _3d_render(mw)
            return shot

        before = render() if moving else None
        if set_up is not None:
            set_up(screen.between)
        image = render()
        for _ in range(RETAKES if before is not None else 0):
            if image != before:
                break
            _settle(DRAW_WAIT)
            image = render()
    if not image.save(out_path):
        raise RuntimeError('could not save the 3D render')
    print("3d render %dx%d (the clipboard's text put back)" % (image.width(), image.height()))
    if before is not None and image == before:
        print(STALE)
