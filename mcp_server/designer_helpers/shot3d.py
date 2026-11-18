"""screenshot_designer('3d') in Designer (shoot_3d): the set-up checked, Designer's window put on screen, transparent,
and kept there until the render is read, the 3D view set up (view3d.py), and a render that may not have followed the
set-up said (REVIEW.md SRV-146, HLP-124).

Measured on macOS in a Designer an agent started (2026-11-13 and 2026-11-14), by panning the view with the helpers' own
drag and comparing its renders. The self-test's editor_panels_and_fit re-measures the first point (minimized and
hidden; covered by a window of Designer's own, it says what it saw) and the second, but for its time, the identical
render and the window never shown. It also
re-measures drags reaching the camera off screen, the top-level window and the page as macOS minimizes it, and AppKit's
notifications coming once the state each wait looks at has changed. The rest was measured once.

- The 3D view's render (Copy Render to Clipboard) is the last frame the view drew while Designer's main window isn't
  on screen: minimized, fully covered by another window (Designer's own or another app's), or Designer hidden. A
  window partly covered draws. Fully covered, in Designers `open` started (launch_designer's), it drew in some, 6 of 6
  tries: Qt kept the window exposed, 3 s after macOS counted it covered in the 3 tries that waited. In others it didn't,
  as Qt no longer exposed it, 6 of 6 tries; each in one Designer (REVIEW.md SRV-152, TST-433; 2026-11-15 and
  2026-11-16). What decides it isn't known, and the shot brings a covered window in front either way. This bullet's other facts were measured in
  Designers started from their binary. Drags given meanwhile reach the camera: the view shows them once it draws
  again, within 0.25 s of the window coming on screen.
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
  False, and its own showNormal() does nothing. The page minimized by Qt itself (showMinimized()) is still exposed;
  its view was seen to stop drawing in some runs and not in others, and nothing says when (2026-11-15: REVIEW.md
  TST-420), so the shot restores the page whatever it draws. Forcing a redraw (update(), repaint(), requestUpdate(),
  an expose event) drew no frame.
- So macOS is asked (_MacWindow, mac_window.py): the window's isMiniaturized and occlusionState, the app's isHidden.
  orderFrontRegardless brings the window in front, un-minimized too, without making Designer the active app: the app
  in front kept it. unhideWithoutActivation shows a hidden Designer the same way. The window was exposed about 0.3 s
  after either. macOS says a window is covered 0.04 to 0.07 s after it is, idle and under load. A window minimized
  both by macOS and by Qt came back the same way, Qt's restore first, Designer still not active.
- unhideWithoutActivation takes effect as Designer's events run, not at the call: until then macOS says Designer is
  hidden (isHidden). The main window brought in front at once after the call ended up behind the active app's window,
  and Qt no longer exposed it once that window covered it whole. The view then drew nothing more. That happened in 5 of
  5 tries of a probe and in 19 of 19 tries of the self-test's scratch runs that day, then in none of 2 in a later one,
  the same app active (2026-11-16, REVIEW.md HLP-160). What sets it off isn't known. Brought in front once macOS no
  longer said Designer hidden, the window stayed in front: 5 of 5 tries, each watched 3 s, and in each scratch run
  since. Qt's applicationStateChanged didn't fire for the unhide, and the window's expose events came before it in one
  probe and after it in another. So the shot waits for macOS's flag. No other Qt callback says it, nor the window off
  screen after a minimize or a hide: neither window's windowStateChanged nor visibleChanged fired, and the top-level
  widget's Hide and Show events came for some hides and unhides and not others (2026-11-16, REVIEW.md HLP-173).
  AppKit's notifications say them (mac_window.py, UNHIDDEN and OFF_SCREEN), so the waits look as those come, and every
  TICK ms. Measured with Designer's windows transparent and click-through (2026-11-17, ROADMAP item 101):
  - NSApplicationDidUnhideNotification came with macOS no longer saying Designer hidden, 5 of 5;
  - NSWindowDidMiniaturizeNotification came once the window server no longer listed the window, before the occlusion
    change: after miniaturize: (the shot's) 6 of 6, after performMiniaturize: (the self-test's minimized way) 3 of 3;
  - NSWindowDidChangeOcclusionStateNotification came once it no longer listed it, after a hide 4 of 4, after a
    minimize 9 of 9. It came with macOS no longer saying the window covered once orderFrontRegardless showed it in
    front of a window of Designer's own covering it whole, 4 of 4: the self-test's uncovered looks as it comes;
  - NSApplicationDidHideNotification came while it still listed the window, 4 of 4: the wait doesn't look as it comes.
    It came with macOS saying Designer hidden, 4 of 4: the self-test's waits for that flag look as it comes (HIDDEN);
  - NSWindowDidDeminiaturizeNotification came with macOS no longer saying the window minimized: after deminiaturize:
    5 of 5, after orderFrontRegardless 4 of 4. The self-test's waits for that look as it comes (UNMINIMIZED).
- A hidden Designer shown again that way, its windows transparent and its main window ordered in front, sometimes
  wasn't drawn: 0.5 s on, Designer was no longer hidden and CoreGraphics listed the window on screen, but macOS still
  counted it covered (occlusionState), so Qt never exposed it. That happened in 3 of 14 runs of the self-test's
  focus check, each in a Designer just started. Ordered in front again then, it was exposed within 0.06 s, 3 of 3
  (2026-11-14, REVIEW.md HLP-145). The same steps run alone never did it, in 33 tries: what sets it off isn't known.
  Since the shot waits for the unhide first (HLP-160), the window was exposed at its first show in 60 of 60 waits,
  over 30 shots of a hidden Designer in 10 Designers just started (2026-11-16, REVIEW.md HLP-173). So it is put in
  front again only once the wait's limit has passed, not after a time measured here.
- Two renders of an unchanged view are identical, pixel for pixel. A pan, an orbit or a zoom changes the render, and
  so does another mesh: Plane and Plane (hi-res), from the top, differ by 0.005 grey levels on average.

Only the main window is looked at: a 3D View panel floating in a window of its own wasn't measured. Elsewhere than
macOS nothing was measured: the window is left as it is, and the shot taken as before.
"""

import contextlib
from collections.abc import Iterator

from .core import Callable, QtCore, QtGui, QtWidgets, Sequence, _main_window, cast
from .frames3d import _Frames, _frames_of, _viewport
from .mac_window import _mac_window, _MacWindow, _wait_unhidden, _wait_unlisted
from .screenshots import _3d_dock, _3d_render
from .view3d import _3d_set_up
from .waits import _event_signal, _until, _unwatch

ON_SCREEN_WAIT = 3.0  # s at most for Designer's window to be on screen once shown, a safety net: about 0.3 s measured
RETAKES = 3  # renders taken again while identical to the one before a set-up that changed what the view shows
BRINGS = 3  # times one look puts the window on screen, when it goes off screen again as the view draws (HLP-163)
WINDOW = "Designer's window: "
STALE = (
    '3D render: identical to the render before the set-up, though the set-up moved the camera, switched the mesh, or '
    'changed the tiling or the light. '
    'The 3D view may not have been drawn. Shoot again with no set-up before judging it: pan, orbit and zoom move the '
    'camera from where it is. With no mesh in view, a pan or zoom changes nothing, and a tiling changes nothing on a '
    'material with no pattern'
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
        # in some Designers launch_designer opened, a covered window's view drew (REVIEW.md TST-433)
        'brought in front, transparent and without taking focus, as its 3D view may not be drawn while covered',
        'brought in front again, transparent, as another window covered it during the shot',
    ),
}
# the page minimized by Qt (no user does that), restored by Qt in a window macOS shows
QT_RESTORED = (
    "un-minimized, as its 3D view isn't drawn while minimized; it stays so",
    'un-minimized again, as it was minimized during the shot; it stays so',
)


def _wait_on_screen(
    mw: QtWidgets.QMainWindow,
    show: Callable[[], None],
    frames: _Frames,
    since: tuple[int, int],
) -> None:
    """Waits for Designer's main window to be on screen (exposed: Qt's expose events), then for the 3D view to draw
    what changed while it was off screen (_Frames.shown, its paints after `since`). A window still not exposed once
    ON_SCREEN_WAIT has passed is put in front again (`show`), once, then refused after ON_SCREEN_WAIT more: macOS once
    counted it covered until then (the module docstring). In some Designers `open` started, Qt kept a covered window
    exposed while macOS counted it covered, and its view drew then too; in others it didn't (REVIEW.md SRV-152,
    TST-433)."""
    handle = mw.windowHandle()
    spy = _event_signal(handle, ('Expose',))
    try:
        if not _until(handle.isExposed, ON_SCREEN_WAIT, [spy.fired]):
            show()  # the limit, a safety net, passed: not a time measured here (REVIEW.md HLP-173)
            if not _until(handle.isExposed, ON_SCREEN_WAIT, [spy.fired]):
                raise RuntimeError(
                    "the 3D view isn't drawn: Designer's window isn't on screen %g s after it was shown again; ask "
                    'the user to show it' % ON_SCREEN_WAIT
                )
    finally:
        _unwatch(handle, spy)
    frames.shown(since)


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
    - a hidden Designer is shown, every window of its own transparent, since all come back, then hidden again. Its
      window is brought in front once macOS says the unhide took (REVIEW.md HLP-160);
    - a page Qt minimized (no user does it) is restored by Qt, in a window macOS shows, and stays so. Its window is
      brought in front too, opaque, and left there: restored by Qt alone, the view drew no new frame.

    Each window is made opaque and clickable again once the window is back, minimized or hidden ones once off screen:
    before, the user would see them. again() looks before each set-up step and render, and after a viewpoint's turn: a
    window the user covered, minimized or hid during the shot is put on screen the same way (REVIEW.md HLP-124,
    HLP-158, HLP-163). A Designer the user made the active app during
    the shot is left on screen, opaque (REVIEW.md HLP-125). It is made opaque at once, by between() before each
    set-up step and render: left transparent, the user would see no window, and a click would go through it to the app
    under it (REVIEW.md HLP-136). While Designer is that app, a window put on screen again isn't made transparent. A
    Designer the active app as the shot began counts as made the active app once the user comes back to it, if a
    look before a step or render saw them gone (REVIEW.md HLP-138). Refused when the window still isn't on screen once
    _wait_on_screen gives up, or goes off screen again as its view draws each of BRINGS times it is put there."""

    def __init__(self, mw: QtWidgets.QMainWindow, mac: _MacWindow | None, frames: _Frames) -> None:
        self._mw = mw
        self._mac = mac
        self._frames = frames  # the 3D view's, watched: its waits once the window is on screen
        self._was_active = mac is not None and mac.active()
        self._hidden = False  # Designer was shown: hidden again after
        self._minimized = False  # the window was shown: minimized again after
        self._covered = False  # the window was brought in front: put back after
        self._covers: list[int] = []  # the numbers of the windows found in front of it, each time it was brought
        self._faded: dict[int, tuple[float, bool]] = {}  # windows made transparent, held, and how each looked before
        self.done = False  # put_back ran to its end

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

    def _bring(self, again: bool, brings: int = BRINGS) -> None:
        """Puts the window on screen, transparent, if it isn't, saying so: the first time, or `again` during the
        shot. Off screen again as the view draws what changed (the user covered, minimized or hid it), it is put on
        screen again, `brings` times in all, then refused (REVIEW.md HLP-163)."""
        mac = self._mac
        if mac is None:
            return
        since = self._frames.mark()  # the paints from here on: the window shown below
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
                # in front before, the window went behind the active app's (REVIEW.md HLP-160)
                _wait_unhidden(mac, ON_SCREEN_WAIT)
            mac.show()
        elif qt:  # restored by Qt alone, the view drew no new frame; brought in front too, it drew (2026-11-14)
            mac.show()
        if qt or minimized or hidden or covered:
            _wait_on_screen(self._mw, mac.show, self._frames, since)
            if self._frames.off_screen():
                if brings <= 1:
                    raise RuntimeError(
                        "the 3D view isn't drawn: Designer's window went off screen again while its view drew, each "
                        'of the %d times it was put on screen; shoot again' % BRINGS
                    )
                # the user may have made Designer the active app meanwhile: made opaque first, as at each look
                # (REVIEW.md HLP-172)
                self.between()
                self._bring(again=True, brings=brings - 1)

    def again(self) -> None:
        """Before a set-up step or a render: makes the windows opaque once the user made Designer the active app
        (between), then puts the window on screen again if it went off screen during the shot."""
        self.between()
        self._bring(again=True)

    def _wait_off_screen(self) -> None:
        """Waits, at most ON_SCREEN_WAIT, for the window to be off screen once minimized or hidden again, as the window
        server lists it (_wait_unlisted)."""
        _wait_unlisted(cast(_MacWindow, self._mac), ON_SCREEN_WAIT)

    def put_back(self) -> None:
        """Puts the window back as it was found off screen: minimized again, behind the windows that were in front of
        it, Designer hidden again. Leaves it on screen when the user made Designer the active app meanwhile, and in
        front when none of the windows that were in front of it is still on screen, or none was found. Then makes each
        window opaque and clickable again (unfade), a minimized or hidden one once off screen; a step that raised, at
        once. An abort cutting the steps short leaves the looks as they are: _on_screen's handler runs this again,
        untraced, each step safe to repeat (REVIEW.md HLP-180: the handler gave the looks back where the window was)."""
        mac = self._mac
        if mac is None:
            return
        try:
            self._sent_back(mac)
        except Exception:  # the looks back still, wherever the window is: transparent, it would look gone
            self.unfade()
            self.done = True  # a step's own error, not tried again
            raise
        self.unfade()
        self.done = True

    def _sent_back(self, mac: _MacWindow) -> None:
        """put_back's steps, and the wait for the window off screen once minimized or hidden again."""
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


@contextlib.contextmanager
def _on_screen(mw: QtWidgets.QMainWindow, frames: _Frames) -> Iterator[_Screen]:
    """Designer's main window on screen while the 3D view is set up and rendered (_Screen): put there now, and again
    before each set-up step and render (_Screen.again), each time waited for on `frames`, the 3D view's. Off screen, the render is the
    view's last frame (the module docstring). The window is put back when the shot fails or is aborted too."""
    screen = _Screen(mw, _mac_window(mw), frames)
    try:
        try:
            screen.opaque_first()
            screen._bring(again=False)
            yield screen
        finally:
            screen.put_back()
    except BaseException:
        # an abort fires once, so this handler runs untraced (the plugin's _make_tracer). Landed in put_back, it cut
        # its steps short, or its looks: put back again, unless it was (REVIEW.md HLP-180). Landed before put_back's
        # `try` or in opaque_first, this gives the looks back, and finishes opaque_first's change, which nothing
        # records (REVIEW.md HLP-135)
        if not screen.done:
            screen.put_back()
        screen.opaque_first()
        raise


def shoot_3d(
    out_path: str,
    graph: str | None = None,
    mesh: str | None = None,
    view: str | None = None,
    zoom: int = 0,
    tiling: float | None = None,
    orbit: Sequence[float] | None = None,  # a tuple from screenshot_designer (REVIEW.md HLP-188)
    pan: Sequence[float] | None = None,
    environment: str | None = None,
    environment_rotation: float | None = None,
    environment_exposure: float | None = None,
) -> None:
    """screenshot_designer('3d'): the 3D view set up when anything is given (_3d_set_up, set_3d_view's steps), then its
    render saved to `out_path`, with Designer's window on screen throughout (_on_screen, looked at again before each
    set-up step and render). What _3d_set_up checks, and a 3D View panel not shown, is refused first, before the window changes
    (REVIEW.md HLP-127). What the steps find as they go is refused after, the window's lines in the error: with mesh=
    and tiling=, the new mesh's material; with graph=, its row in the Explorer; with the environment, its fields in the
    Parameters panel and a map the 3D view doesn't take. After a set-up that changed what the view shows (the camera
    moved, the mesh switched, the tiling or the light changed: the set-up's run says), a render identical to the one
    before it is taken again, at most RETAKES times, each once the view drew another frame, then said (STALE): the view
    may not have been drawn. It isn't taken again once the view draws no frame within NO_RESTART (_Frames.next_frame;
    off screen, at once). A view or a graph may already be what is shown, so they are no sign; nor are a value shown
    already or a map asked again, which the set-up says changed nothing. Each wait is on the view's frames, watched from before the window is put on screen until the render
    (frames3d.py; REVIEW.md HLP-148)."""
    light = (environment, environment_rotation, environment_exposure)
    given = bool(graph or mesh or view or zoom or orbit or pan) or any(v is not None for v in (tiling, *light))
    set_up = _3d_set_up(graph, mesh, view, zoom, tiling, orbit, pan, *light) if given else None
    mw = _main_window()
    dock = _3d_dock(mw)  # held: without, the viewport's wrapper went stale
    frames = _frames_of(mw, _viewport(dock))
    try:
        with _on_screen(mw, frames) as screen:

            def render() -> QtGui.QImage:
                screen.again()
                return _3d_render(mw)

            # a set-up that may change what the view shows: a render before it, compared once it says it did
            before = render() if set_up is not None and set_up.may_change else None
            changed = False
            if set_up is not None:
                # before each step, the window put on screen again if it went off, as before a render: a camera's
                # turn is watched on screen (REVIEW.md HLP-158, the user's choice)
                changed = set_up(screen.again, frames)
            image = render()
            compared = before is not None and changed
            for _ in range(RETAKES if compared else 0):
                if image != before or not frames.next_frame():
                    break
                image = render()
    finally:
        frames.close()
    if not image.save(out_path):
        raise RuntimeError('could not save the 3D render')
    print("3d render %dx%d (the clipboard's text put back)" % (image.width(), image.height()))
    if compared and image == before:
        print(STALE)
