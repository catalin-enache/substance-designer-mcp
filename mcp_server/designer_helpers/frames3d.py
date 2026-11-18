"""The 3D view's frames, watched while screenshot_designer('3d') sets it up and renders it (_Frames): what its waits
wait for, instead of fixed times (REVIEW.md HLP-148).

Measured on macOS in a Designer an agent started, in English (2026-11-15). The self-test's editor_panels_and_fit
re-measures, in its frames fact: the count at rest; its restart by a pan and by a viewpoint, held while the camera
turns, and its return; the first paint after each reading the count from before; a show from hidden right after a
pan made meanwhile (an UpdateRequest, then a restart), and one with nothing changed (only paints at rest); no count
with Display > Samples off, at the frame after the toggle; Designer hidden, an UpdateRequest after each pan and no
paint. Its window checks take a zoom whose window goes off screen at its first step. The rest was measured once.

- Each frame the 3D view draws is a Paint event on its viewport (an Alg::Gui3D::ViewportWidget). Off screen it draws
  none.
- The viewport's overlay labels show "Samples: N" (Display > Samples, on by default): the frames its antialiasing has
  accumulated, 8 at rest with the Rasterizer. A label read as a paint arrives shows the count of the frame before.
  So the first paint after a change still reads the count from before it.
- A pan, an orbit, a wheel step, a mesh, a viewpoint, Frame, a graph's outputs and a tiling each restart the count
  at 1. It then climbs back to 8, and the view stops drawing. A viewpoint or Frame turns the camera, Designer's own
  transition, and the count stays at 1 until the turn ends. The viewpoint the camera already has restarts nothing.
- On screen, each frame of an accumulation is an UpdateRequest event (Qt's, as the view asks for a frame) then its
  paint, about 30 ms apart; after the last one, nothing more comes, so nothing says the accumulation ended but its
  count.
- Designer hidden: nothing changed, no UpdateRequest comes; a pan brings one, a viewpoint one after another while the
  camera turns.
- Designer's window coming on screen with nothing changed: three paints reading the count at rest, and no
  UpdateRequest, in each of 5 shows. Coming on screen with the count left lower (Designer hidden mid-accumulation), the
  count went on to 8, and in 1 show of 5 two paints read the lower count first, before any UpdateRequest (2026-11-16,
  REVIEW.md HLP-167). With something changed while the window was off screen (a pan, a viewpoint, a
  graph's outputs; hidden or minimized), the view asks for a frame or restarts by the second paint, in each of 9
  shows where the change's UpdateRequest had come while hidden (the shot's moves wait for it: taken). A pan made right
  before the show, its UpdateRequest not come yet, read the count at rest at the first three paints, then asked.
- With Display > Samples off, the label shows no count, only "Render Time". It changes at the next frame, not as the
  menu is toggled. The GPU Pathtracer counts on: 143 samples after 6 s.
- The label changes only at a frame, so off screen it stays at the count of the last frame drawn there. After the
  self-test's material check (Materials > Add, whose dialog shows Designer, then Designer hidden again), it read
  "Samples: 1", "Samples: 3" and "Samples: 2" in three tries.
- A drag, or a wheel step, sent before the view drew a frame after the one before is lost, or part of it. Sent after
  that frame, each was taken as when they were 0.2 s apart: the renders were identical.
- Designer hidden, the view draws no frame, and moves sent back to back were lost too: three pans, or three wheel
  steps, a pan and a turn, came out 22 to 25 grey levels apart on average from the same moves 0.2 s apart. Each move
  was followed by one UpdateRequest, 0.02 to 0.04 s later, and moves sent each after it came out as those 0.2 s apart
  (within 0.01 grey levels on average; 2026-11-15). The UpdateRequest came while the move's own events ran in 1 of 60
  moves, the first (2026-11-16, REVIEW.md HLP-164).
- Off screen, the same set-up from the same start still came out differently between runs: a pan of two drags 68.5
  grey levels away in 1 run of 2, a mesh switch and an orbit in one call 1.1 and 4.2 apart. On screen, each of 5
  set-ups repeated exactly, twice (2026-11-16). So set_3d_view runs a set-up that moves the camera with the window on
  screen (view3d.py; REVIEW.md HLP-168, the user's choice).
- On screen, waits that counted the frames drawn while a move's events ran lost one of zoom=-3's three wheel steps:
  it zoomed out 0.82x, as two steps do, once (2026-11-16).
- In a Designer launch_designer opened hidden, before any shot, the overlay's labels were empty: the view hadn't drawn.
  After one, they read "Samples: 8" (2026-11-16, REVIEW.md HLP-162).
- Designer in another language than English wasn't measured: a label saying its count otherwise isn't read
  (_samples), and the waits then compare renders.

So the waits (_Frames):
- after a step: the count restarted, then at SAMPLES (the GPU Pathtracer's render is taken there, the user's choice),
  or the restart's paint and the view off screen, which Qt's expose events say: a label left lower (Designer hidden
  mid-accumulation) draws nothing more. Off screen, where the view draws no paint, an UpdateRequest since the step
  says it took the step (REVIEW.md HLP-158). An accumulation that ends lower on screen (a renderer setting; not
  measured) is waited for SETTLE_LIMIT. A step that restarts nothing within NO_RESTART changed nothing the view shows
  (REVIEW.md HLP-151: the view quiet for a poll's interval ended these waits, a time). A restart is a count that drops
  from the one before it: a count still climbing from the step before isn't one (REVIEW.md HLP-159);
- after a viewpoint, before Frame: the count rising after its restart, the turn over (a Frame at once cancels it).
  Off screen nothing says the turn ended. Measured hidden (2026-11-16, 2 turns): only UpdateRequests came, every 22 to
  44 ms, for 0.82 and 0.84 s, then nothing; no other event on the viewport or its window. So the set-up shows the
  window for the turn (view3d.py's _3d_set_up, the user's choice: REVIEW.md HLP-158). Gone off screen during it, the
  wait ends, and the set-up's look after the turn puts the window on screen again and waits for the view to settle
  there (REVIEW.md HLP-163);
- after a drag or a wheel step: a frame after the move's events ran; off screen, an UpdateRequest since the move began
  (taking; REVIEW.md HLP-164);
- once the window is on screen: a restart and the count back; or, from a count at rest, two paints reading no restart
  and no UpdateRequest since the show, what tells nothing changed from a change made while it was off screen
  (REVIEW.md HLP-151); from a count left lower, the count at the target (REVIEW.md HLP-167). A change
  made right before the show by something else than the shot, its UpdateRequest not come yet, isn't told. With no
  count shown yet, the paint after the view's first frame says whether one shows (REVIEW.md HLP-162). With no
  count to read, renders are compared every TICK ms instead, taken between looks, never in a wait's state (a
  render runs Designer's events itself): two renders alike, no change needed first (REVIEW.md HLP-174). The wait
  ends as the window goes off
  screen again, and the shot puts it on screen again (shot3d.py; REVIEW.md HLP-163);
- with no count to read, a step's comparison of renders ends off screen on an UpdateRequest since the step, as the
  count's wait does: off screen every render is the view's last frame (REVIEW.md HLP-163). Off screen from the step
  on, it takes no render: a view that never drew, as in a Designer opened hidden before any 3D shot, gives none
  there, and set_3d_view raised after switching the mesh (REVIEW.md HLP-170).
"""

from types import TracebackType

from .core import Callable, QtGui, QtWidgets, cast
from .screenshots import _3d_render
from .waits import TICK, _event_signal, _settle, _until, _unwatch

SAMPLES = 8  # the count a settled view is waited for: the Rasterizer's at rest; the GPU Pathtracer counts on
NO_RESTART = 1.0  # s a step's change may take to show: a step that restarts nothing changed nothing the view shows
SETTLE_LIMIT = 3.0  # s at most for the view to settle once it restarted: a safety net
COUNT = r'Samples: (\d+)'  # the overlay's line, in English
VIEWPORT = 'Alg::Gui3D::ViewportWidget'


def _samples(texts: list[str]) -> int | None:
    """The count the 3D view's overlay shows, from its labels' `texts`; None when none shows one."""
    import re

    for text in texts:
        found = re.search(COUNT, text)
        if found:
            return int(found.group(1))
    return None


class _Counts:
    """The counts read at the 3D view's paints (`seen`, in order, None where no count showed), and what they say since
    a mark: the index of the first paint after it."""

    def __init__(self, target: int = SAMPLES) -> None:
        self.target = target
        self.seen: list[int | None] = []

    def restart(self, since: int) -> int | None:
        """The index of the first paint since `since` reading a count below the target and below the count read before
        it, at any paint: the view restarted. A count still climbing from a step before isn't a restart (REVIEW.md
        HLP-159: a mark taken mid-accumulation read the count left over as the next step's restart)."""
        before = self._before(since)
        for i in range(since, len(self.seen)):
            count = self.seen[i]
            if count is None:
                continue
            if count < self.target and (before is None or count < before):
                return i
            before = count
        return None

    def _before(self, since: int) -> int | None:
        """The count read last before `since`; None when none was."""
        return next((c for c in reversed(self.seen[:since]) if c is not None), None)

    def _after_restart(self, since: int, at_least: int) -> bool:
        first = self.restart(since)
        return first is not None and any(c is not None and c >= at_least for c in self.seen[first + 1 :])

    def settled(self, since: int, off: bool = False) -> bool:
        """The view restarted since `since`, then counted back to the target, or is now `off` screen, where it draws
        nothing more (a label left lower). The restart's paint reads the count of the frame before it, the restart's,
        so the change was drawn by then (REVIEW.md HLP-158: a frame more was waited for)."""
        return self._after_restart(since, self.target) or (off and self.restart(since) is not None)

    def moved(self, since: int) -> bool:
        """The view restarted since `since`, then counted higher than its restart: the camera stopped turning."""
        first = self.restart(since)
        return first is not None and self._after_restart(since, cast(int, self.seen[first]) + 1)

    def unchanged(self, since: int) -> bool:
        """Two paints since `since`, neither reading a restart: the first frame drawn restarted nothing."""
        return len(self.seen) - since >= 2 and self.restart(since) is None

    def shown(self, since: int, asked: bool) -> bool:
        """Designer's window shown at `since`: the view restarted and settled, or an accumulation left lower off screen
        went on to the target (no restart there: REVIEW.md HLP-159), or, from a count at rest or none read, its paints
        read no restart (unchanged) and the view asked for no frame since (`asked`: an UpdateRequest). From a count left
        lower, paints reading it say nothing yet: the view goes on to the target (REVIEW.md HLP-167)."""
        before = self._before(since)
        at_rest = before is None or before >= self.target
        return self.settled(since) or self._went_on(since) or (at_rest and self.unchanged(since) and not asked)

    def _went_on(self, since: int) -> bool:
        """The count read before `since` was below the target, and a paint since reads the target."""
        before = self._before(since)
        return (
            before is not None
            and before < self.target
            and any(c is not None and c >= self.target for c in self.seen[since:])
        )


def _viewport(dock: QtWidgets.QDockWidget) -> QtWidgets.QWidget:
    """The 3D view's viewport in its `dock`, the one the set-up drags (_3d_set_up); refused when there is none."""
    # className() is a str: PySide's stubs say bytes
    found = [w for w in dock.findChildren(QtWidgets.QWidget) if cast(str, w.metaObject().className()) == VIEWPORT]
    if not found:
        raise RuntimeError("the 3D View's viewport wasn't found")
    return found[0]


class _Frames:
    """The 3D view's frames, watched from now until close(): the count its overlay shows read at each paint (_Counts),
    and the waits on them (the module docstring). `render` takes a render, for the comparison where no count shows."""

    def __init__(self, viewport: QtWidgets.QWidget, render: Callable[[], QtGui.QImage]) -> None:
        import weakref

        self._viewport = viewport
        self._labels = viewport.findChildren(QtWidgets.QLabel)
        self._render = render
        # None while no count has shown, renders compared then; made at the paint reading the first (REVIEW.md
        # HLP-162: in a Designer opened hidden, the labels are empty until the view has drawn)
        self._counts: _Counts | None = None
        self._painted = 0  # paints seen
        self._asked = 0  # UpdateRequests seen: the view asking for a frame
        if self.count() is not None:
            self._counts = _Counts()
        # the spy holds its callback, so it holds this watch only weakly: dropped without close(), as after an abort,
        # the watch and its spy go at once, the viewport's filter with them (REVIEW.md HLP-165)
        event = weakref.WeakMethod(self._event)

        def seen(kind: str) -> None:
            bound = event()
            if bound is not None:
                bound(kind)

        self._spy = _event_signal(viewport, ('Paint', 'UpdateRequest'), seen)
        # what _drawing() reads changes with these, so the waits look again at each (REVIEW.md HLP-158)
        self._window = viewport.windowHandle()
        self._exposed = _event_signal(self._window, ('Expose',))

    def count(self) -> int | None:
        """The count the overlay shows now; None when it shows none."""
        return _samples([label.text() for label in self._labels])

    def _event(self, kind: str) -> None:
        if kind == 'UpdateRequest':
            self._asked += 1
            return
        self._painted += 1
        count = self.count()
        if self._counts is None and count is not None:  # the paints before showed none
            self._counts = _Counts()
            self._counts.seen.extend([None] * (self._painted - 1))
        if self._counts is not None:
            self._counts.seen.append(count)

    def close(self) -> None:
        """Stops watching."""
        _unwatch(self._viewport, self._spy)
        _unwatch(self._window, self._exposed)

    def _wait(self, state: Callable[[], bool], limit: float) -> bool:
        return _until(state, limit, [self._spy.fired, self._exposed.fired])

    def mark(self) -> tuple[int, int]:
        """Where the paints and the UpdateRequests after now start, for the waits after a change."""
        return self._painted, self._asked

    def _drawing(self) -> bool:
        return bool(self._viewport.windowHandle().isExposed())

    def next_frame(self) -> bool:
        """Waits for the view's next frame, at most NO_RESTART; at once when the view is off screen, where it draws
        none. Returns whether one came."""
        if not self._drawing():
            return False
        since = self._painted
        return self._wait(lambda: self._painted > since, NO_RESTART)

    def taken(self, since: tuple[int, int]) -> bool:
        """After a drag or a wheel step: waits for the view to take it, at most NO_RESTART. On screen, that is a frame
        after the paints `since` counts. Off screen, where it draws none, it is an UpdateRequest after those `since`
        counts, the view asking for a frame. Returns whether either came (REVIEW.md HLP-149)."""
        painted, asked = since
        return self._wait(lambda: self._painted > painted or (self._asked > asked and not self._drawing()), NO_RESTART)

    def taking(self) -> Callable[[], bool]:
        """Before a drag or a wheel step: returns the wait for the view to take it (taken), run once the move's events
        ran. Its UpdateRequests count from now: off screen, the view's can come while those events run (REVIEW.md
        HLP-164). Its paints count from the wait's start: on screen, counted from now, a zoom lost one of its wheel
        steps (the module docstring)."""
        asked = self._asked
        return lambda: self.taken((self._painted, asked))

    def settled(self, since: tuple[int, int]) -> None:
        """After a step: waits for the view to restart since `since`, at most NO_RESTART (none: the step changed
        nothing it shows), then to count back to the count at rest, at most SETTLE_LIMIT. Off screen, where the view
        draws no paint, an UpdateRequest since `since` ends both (REVIEW.md HLP-158)."""
        paints, asked = since

        def asked_off_screen() -> bool:
            return self._asked > asked and not self._drawing()

        counts = self._counts
        if counts is None:
            self._renders_alike(asked_off_screen)
            return
        if self._wait(lambda: counts.restart(paints) is not None or asked_off_screen(), NO_RESTART):
            self._wait(lambda: counts.settled(paints, not self._drawing()) or asked_off_screen(), SETTLE_LIMIT)

    def moved(self, since: tuple[int, int]) -> None:
        """After a viewpoint: waits for the camera's turn to end (_Counts.moved), as settled() does for its count. Ends
        as the view goes off screen, where nothing says the turn ended: the set-up's look after the turn puts the window
        on screen again and waits for the view there (view3d.py; REVIEW.md HLP-163)."""
        off = self.off_screen
        counts = self._counts
        if counts is None:
            self._renders_alike(off)
            return
        paints = since[0]
        if self._wait(lambda: counts.restart(paints) is not None or off(), NO_RESTART):
            self._wait(lambda: counts.moved(paints) or off(), SETTLE_LIMIT)

    def shown(self, since: tuple[int, int]) -> None:
        """Once Designer's window is on screen again, shown after `since`: waits for the view to draw what changed
        meanwhile, if anything did (the module docstring), at most SETTLE_LIMIT. Ends as the view goes off screen
        again (REVIEW.md HLP-163): the caller puts it on screen again (shot3d.py)."""
        off = self.off_screen
        paints, asked = since
        if self._counts is None:  # a label shows its count from the view's first frame on (REVIEW.md HLP-162)
            self._wait(lambda: self._counts is not None or self._painted > paints + 1 or off(), SETTLE_LIMIT)
        counts = self._counts
        if counts is None:
            if not off():
                self._renders_alike(off, changed=False)
            return
        self._wait(lambda: counts.shown(paints, self._asked > asked) or off(), SETTLE_LIMIT)

    def off_screen(self) -> bool:
        """Whether the view is off screen, where it draws nothing: Qt no longer exposes its window."""
        return not self._drawing()

    def _renders_alike(self, ended: Callable[[], bool], changed: bool = True) -> None:
        """Where no count shows, a poll: a render every TICK ms until one is like the one before, after one changed
        when `changed` (a change shown); none changed within NO_RESTART: nothing changed. At most SETTLE_LIMIT more.
        Ends too once `ended()` says so, looked at after each poll: off screen each render is the view's last frame
        (REVIEW.md HLP-163). Off screen from the start, it takes no render there, as a view that never drew gives none
        (REVIEW.md HLP-170): it waits for `ended()`, at most NO_RESTART, or for the window on screen, where the renders
        are compared in the time left (REVIEW.md HLP-176: the user showing Designer meanwhile, it waited the whole
        NO_RESTART, then compared none). The renders are taken here, between looks, never in a wait's state: a render
        runs Designer's events itself."""
        import time

        start = time.monotonic()
        if not self._drawing():
            self._wait(lambda: ended() or self._drawing(), NO_RESTART)
            if ended() or not self._drawing():
                return
        last = self._render()
        seen = not changed
        while time.monotonic() - start < NO_RESTART + SETTLE_LIMIT:
            if not seen and time.monotonic() - start >= NO_RESTART:
                return
            _settle(TICK / 1000.0)
            if ended():
                return
            image = self._render()
            same = image == last
            last = image
            if not same:
                seen = True
            elif seen:
                return


def _frames_of(mw: QtWidgets.QMainWindow, viewport: QtWidgets.QWidget) -> _Frames:
    """The 3D `viewport`'s frames, watched from now (_Frames); where no count shows, the renders compared are taken
    from Designer's main window `mw` (_3d_render). The 3D shot and the 3D view's set-up watch the view this way."""
    return _Frames(viewport, lambda: _3d_render(mw))


class _Waiting:
    """`with _Waiting(watched) as waiting:` around a change: on leaving, the change is waited for on `watched`, the view
    restarting and settling since a mark taken as the `with` starts (_Frames.settled). A step of the 3D view's set-up waits this
    way (view3d.py). Inside, the step records the change once made, so an error in its wait can say it was set
    (REVIEW.md HLP-200). `waiting.needed` set False skips the wait, for a change the view takes as none (REVIEW.md
    HLP-201). An error inside skips it too."""

    def __init__(self, watched: _Frames) -> None:
        self.watched = watched
        self.needed = True
        self.since = watched.mark()

    def __enter__(self) -> '_Waiting':
        return self

    def __exit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        if kind is None and self.needed:
            self.watched.settled(self.since)
