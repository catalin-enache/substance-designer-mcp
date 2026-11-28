"""The 3D view's frames, watched while screenshot_designer('3d') sets it up and renders it (_Frames): what its waits
wait for, instead of fixed times (REVIEW.md HLP-148).

Measured on macOS in a Designer an agent started, in English (2026-11-15). The self-test's editor_panels_and_fit
re-measures, in its frames fact: the count at rest; its restart by a pan and by a viewpoint, held while the camera
turns, and its return; the first paint after each reading the count from before; a show from hidden right after a
pan made meanwhile (an UpdateRequest, then a restart), and one with nothing changed (only paints at rest); no count
with Display > Samples off, at the frame after the toggle; Designer hidden, an UpdateRequest after each pan and no
paint. The rest was measured once.

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
  shows where the change's UpdateRequest had come while hidden. A pan made right
  before the show, its UpdateRequest not come yet, read the count at rest at the first three paints, then asked.
- With Display > Samples off, the label shows no count, only "Render Time". It changes at the next frame, not as the
  menu is toggled. The GPU Pathtracer counts on: 143 samples after 6 s.
- The Rasterizer's Samples (Renderer > Edit settings, the Parameters panel's Rasterizer page), 8 by default, set to 4
  stopped the count at 4. With its "Enable rasterizer accumulation antialiasing" off, each frame read 1 (2026-11-21,
  REVIEW.md HLP-211). At Samples 4, each wheel notch on screen drew 6 paints reading 4, 1, 1, 2, 3, 4, and hidden one
  UpdateRequest and no paint. With antialiasing off, each notch drew 3 or 4 paints on screen, each reading 1, and
  hidden one UpdateRequest. Samples above 8 weren't measured. The self-test's Rasterizer check (editor_panels_and_fit)
  re-measures the count at the render, 4 then 1, with an on-screen zoom at each.
- The label changes only at a frame, so off screen it stays at the count of the last frame drawn there. After the
  self-test's material check (Materials > Add, whose dialog shows Designer, then Designer hidden again), it read
  "Samples: 1", "Samples: 3" and "Samples: 2" in three tries.
- A pan made by the mouse, Designer hidden: the view draws no frame, and asks for one (an UpdateRequest) 0.02 to 0.04 s
  after the pan (2026-11-15). Of 60 moves, wheel notches and drags in turn, it came while the move's own events ran
  in 1, the first (2026-11-16, REVIEW.md HLP-164). The self-test's window checks pan so, a change no shot makes (its camera goes through the state file:
  scene3d.py).
- A load of the 3D view's state file restarts the count, which holds at 1 while the camera glides to the file's
  pose, then climbs back (scene3d.py).
- In a Designer launch_designer opened hidden, before any shot, the overlay's labels were empty: the view hadn't drawn.
  After one, they read "Samples: 8" (2026-11-16, REVIEW.md HLP-162).
- Designer in another language than English wasn't measured: a label saying its count otherwise isn't read
  (_samples), and the waits then compare renders.

So the waits (_Frames):
- after a step: the count restarted, then at SAMPLES (the GPU Pathtracer's render is taken there, the user's choice),
  or the restart's paint and the view off screen, which Qt's expose events say: a label left lower (Designer hidden
  mid-accumulation) draws nothing more. Off screen, where the view draws no paint, an UpdateRequest since the step
  says it took the step (REVIEW.md HLP-158). A step that restarts nothing within NO_RESTART changed nothing the view shows
  (REVIEW.md HLP-151: the view quiet for a poll's interval ended these waits, a time). A restart is a count that drops
  from the one before it: a count still climbing from the step before isn't one (REVIEW.md HLP-159);
- the count at rest is SAMPLES, whatever the Rasterizer's settings: the shot reads none of them (REVIEW.md HLP-215,
  the user's choice). With its Samples below 8, or its accumulation antialiasing off, the count stops below SAMPLES on
  screen. At Samples below 8, a settle after a restart runs to its net. The result names the count, off screen the one
  last drawn, and what may hold it there, a view still refining among them (below_rest), claiming neither;
- with the Rasterizer's Samples above 8, if its count goes on past 8 as the GPU Pathtracer's does, the view reads as
  at rest at 8, and a render is taken mid-accumulation (_resting; not measured). With its antialiasing off, each paint
  reads 1. A restart is a count below the one before, so only the watch's first paint, with no count before it, reads
  as one: a wait that sees it, as the first step of a shot in a Designer already on screen, runs to its net and says
  unsettled. A later step's settled and moved can end at NO_RESTART as if the step changed nothing (REVIEW.md
  HLP-216, HLP-217; not measured). The self-test's Rasterizer check measures a zoom then, its count said of a step
  or of the render;
- after a load of the state file: its end (scene3d.py), then the count rising back to SAMPLES after its restart, the
  camera's glide over (settled). Each wait SETTLE_LIMIT at most, a safety net, but a mesh file's import's end,
  scene3d.IMPORT_LIMIT;
- with a count past SAMPLES, as the GPU Pathtracer's, the view reads as at rest while it still accumulates (_resting;
  not measured);
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
  there (REVIEW.md HLP-170).
"""

from types import TracebackType

from .core import Callable, Iterator, QtGui, QtWidgets, cast
from .screenshots import _3d_render
from .waits import TICK, _event_signal, _settle, _until, _unwatch

# the count a settled view is waited for: the Rasterizer's at rest at its defaults; the GPU Pathtracer counts on
SAMPLES = 8
# what a result adds of a count held below SAMPLES (_Frames.below_rest): the count, where it was read, and what may
# hold it there
HELD = (
    ", its sample count at %d%s, below 8: it may still have been refining, or the Rasterizer's Samples may be set below"
    ' 8 or its accumulation antialiasing off (Renderer > Edit settings)'
)
HELD_AGAIN = ', its sample count at %d%s, below 8'  # what may hold it there said once already
LAST_DRAWN = ' when last drawn'  # off screen, where the count stays as the view last drew it
NO_RESTART = 1.0  # s a step's change may take to show: a step that restarts nothing changed nothing the view shows
# s at most for the view to settle once it restarted, or for a load of the state file to end, a mesh file's import
# aside (scene3d.IMPORT_LIMIT): a safety net
SETTLE_LIMIT = 3.0
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

    def _restarts(self, since: int) -> Iterator[int]:
        """The index of each paint since `since` reading a count below the target and below the count read before it,
        in order: each a restart of the view. A count still climbing from a step before isn't a restart (REVIEW.md
        HLP-159: a mark taken mid-accumulation read the count left over as the next step's restart)."""
        before = self._before(since)
        for i in range(since, len(self.seen)):
            count = self.seen[i]
            if count is None:
                continue
            if count < self.target and (before is None or count < before):
                yield i
            before = count

    def restart(self, since: int) -> int | None:
        """The index of the first restart since `since` (_restarts); None when none was."""
        return next(self._restarts(since), None)

    def _before(self, since: int) -> int | None:
        """The count read last before `since`; None when none was."""
        return next((c for c in reversed(self.seen[:since]) if c is not None), None)

    def _reached(self, start: int, at_least: int) -> bool:
        """Whether a paint from index `start` on read a count of `at_least` or more."""
        return any(c is not None and c >= at_least for c in self.seen[start:])

    def settled(self, since: int, off: bool = False) -> bool:
        """The view restarted since `since`, then counted back to the target after its latest restart, or is now `off`
        screen, where it draws nothing more (a label left lower). The restart's paint reads the count of the frame
        before it, the restart's, so the change was drawn by then (REVIEW.md HLP-158: a frame more was waited for).
        The latest: a step that restarts the view more than once counts back after each, and the render must follow
        the last (ROADMAP item 112: it was taken at the last wheel step's first frame, one sample)."""
        latest = max(self._restarts(since), default=None)
        return latest is not None and (self._reached(latest + 1, self.target) or off)

    def moved(self, since: int) -> bool:
        """The view restarted since `since`, then counted higher than its restart: the camera stopped turning."""
        first = self.restart(since)
        return first is not None and self._reached(first + 1, cast(int, self.seen[first]) + 1)

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
        return before is not None and before < self.target and self._reached(since, self.target)


def _viewport(dock: QtWidgets.QDockWidget) -> QtWidgets.QWidget:
    """The 3D view's viewport in its `dock`, the one the set-up watches (scene3d._3d_set_up); refused when there is
    none."""
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
        self._held_said = False  # below_rest said what may hold the count below SAMPLES
        # the mark of the latest look whose wait (shown) ended at its limit; None once a step restarted the view since
        self._unshown: tuple[int, int] | None = None
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

    def until(self, state: Callable[[], bool], limit: float) -> bool:
        """Waits for `state()`, looking at each of the view's paints, UpdateRequests and expose events, at most `limit`
        s, a safety net (waits._until). Returns whether it came."""
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
        return self.until(lambda: self._painted > since, NO_RESTART)

    def _asked_off_screen(self, asked: int) -> bool:
        """Whether the view asked for a frame since it had asked `asked` times, and is off screen, where it draws none:
        the sign off screen that it took a step (REVIEW.md HLP-158)."""
        return self._asked > asked and not self._drawing()

    def _resting(self) -> bool:
        """Whether the overlay's count is at SAMPLES or past it: with the Rasterizer at its defaults, the view drew its
        accumulation's last frame, on screen or before it went off. The GPU Pathtracer counts on past SAMPLES, so its
        view reads as at rest while it still accumulates (the module docstring)."""
        count = self.count()
        return count is not None and count >= SAMPLES

    def below_rest(self) -> str:
        """What a step's result adds when the view shows a count below SAMPLES: the count, and the first time a watch
        says it what may hold it there, claiming neither as the cause (HELD; REVIEW.md HLP-215, the user's choice);
        after that the count alone, as one result may say it of several steps. Off screen, the count is the one last
        drawn, said so (REVIEW.md TST-679: measured, a step refused there read it, 4 and 1). '' with no count, or one at
        SAMPLES or past it."""
        count = self.count()
        if count is None or self._resting():
            return ''
        said, self._held_said = self._held_said, True
        return (HELD_AGAIN if said else HELD) % (count, '' if self._drawing() else LAST_DRAWN)

    def settled(self, since: tuple[int, int]) -> bool:
        """After a step: waits for the view to restart since `since`, at most NO_RESTART (none: the step changed
        nothing it shows), then to count back to the count at rest, at most SETTLE_LIMIT. Off screen, where the view
        draws no paint, an UpdateRequest since `since` ends both (REVIEW.md HLP-158). Returns False when the count
        wasn't back within SETTLE_LIMIT, which the set-up says (REVIEW.md HLP-214); True otherwise."""
        paints, asked = since

        def asked_off_screen() -> bool:
            return self._asked_off_screen(asked)

        counts = self._counts
        if counts is None:
            self._unshown = None  # the step's own wait, its result the step's to say
            return self._renders_alike(asked_off_screen)
        if not self._restart(counts, since):
            return True  # no restart: the step changed nothing the view shows
        self._unshown = None  # restarted: the step's own wait from here on, its result the step's to say
        return self.until(lambda: counts.settled(paints, not self._drawing()) or asked_off_screen(), SETTLE_LIMIT)

    def _restart(self, counts: _Counts, since: tuple[int, int]) -> bool:
        """Waits for the view's restart since `since`, at most NO_RESTART: a paint reading it, or off screen, where the
        view draws no paint, an UpdateRequest (REVIEW.md HLP-158). Returns whether it came."""
        paints, asked = since
        return self.until(lambda: counts.restart(paints) is not None or self._asked_off_screen(asked), NO_RESTART)

    def moved(self, since: tuple[int, int]) -> bool:
        """After a viewpoint: waits for the camera's turn to end (_Counts.moved), as settled() does for its count, and
        returns False as it does. Ends as the view goes off screen, where nothing says the turn ended (REVIEW.md
        HLP-163). The set-up waits with settled(); the self-test's facts measure Designer's own turns with this
        (facts/state_file.py)."""
        off = self.off_screen
        counts = self._counts
        if counts is None:
            self._unshown = None  # as in settled()
            return self._renders_alike(off)
        paints = since[0]
        if not self.until(lambda: counts.restart(paints) is not None or off(), NO_RESTART):
            return True
        self._unshown = None
        return self.until(lambda: counts.moved(paints) or off(), SETTLE_LIMIT)

    def shown(self, since: tuple[int, int]) -> None:
        """Once Designer's window is on screen again, shown after `since`: waits for the view to draw what changed
        meanwhile, if anything did (the module docstring), at most SETTLE_LIMIT. Ends as the view goes off screen
        again (REVIEW.md HLP-163): the caller puts it on screen again (shot3d.py). Records in `undrawn` whether the view
        hadn't drawn it within SETTLE_LIMIT, which the shot says after its render unless a step restarted the view
        since, or the view drew it since (REVIEW.md HLP-214, HLP-222)."""
        off = self.off_screen
        paints = since[0]
        if self._counts is None:  # a label shows its count from the view's first frame on (REVIEW.md HLP-162)
            self.until(lambda: self._counts is not None or self._painted > paints + 1 or off(), SETTLE_LIMIT)

        if self._counts is None:
            drawn = off() or self._renders_alike(off, changed=False)
        else:
            drawn = self.until(lambda: self._look_drawn(since) or off(), SETTLE_LIMIT)
        self._unshown = None if drawn else since

    def _look_drawn(self, since: tuple[int, int]) -> bool:
        """Whether the view drew what changed since a look's mark `since` (_Counts.shown), by the paints and the
        UpdateRequests counted up to now; False where no count shows."""
        counts = self._counts
        return counts is not None and counts.shown(since[0], self._asked > since[1])

    @property
    def undrawn(self) -> bool:
        """Whether the latest look's wait (shown) ended at its limit, no step restarted the view since, and the view
        hasn't drawn what changed by now: the render may be of a view still drawing, which the shot says after it
        (shot3d.UNDRAWN; REVIEW.md HLP-222). The look's own read is read again, on the paints counted since, never the
        count alone: with a frame asked for, a count at SAMPLES may be the one before the change. Measured, forced (3 of
        3), when the zoom was wheel steps: a look ending at its limit, then a step with no sign; the view drew it during
        the step's wait, and the render matched a plain shot right after it. Where no count shows, the look's result
        stands."""
        return self._unshown is not None and not self._look_drawn(self._unshown)

    def off_screen(self) -> bool:
        """Whether the view is off screen, where it draws nothing: Qt no longer exposes its window."""
        return not self._drawing()

    def _renders_alike(self, ended: Callable[[], bool], changed: bool = True) -> bool:
        """Where no count shows, a poll: a render every TICK ms until one is like the one before, after one changed
        when `changed` (a change shown); none changed within NO_RESTART: nothing changed. At most SETTLE_LIMIT more,
        then returns False; True when it ended before (REVIEW.md HLP-214).
        Ends too once `ended()` says so, looked at after each poll: off screen each render is the view's last frame
        (REVIEW.md HLP-163). Off screen from the start, it takes no render there, as a view that never drew gives none
        (REVIEW.md HLP-170): it waits for `ended()`, at most NO_RESTART, or for the window on screen, where the renders
        are compared in the time left (REVIEW.md HLP-176: the user showing Designer meanwhile, it waited the whole
        NO_RESTART, then compared none). The renders are taken here, between looks, never in a wait's state: a render
        runs Designer's events itself."""
        import time

        start = time.monotonic()
        if not self._drawing():
            self.until(lambda: ended() or self._drawing(), NO_RESTART)
            if ended() or not self._drawing():
                return True
        last = self._render()
        seen = not changed
        while time.monotonic() - start < NO_RESTART + SETTLE_LIMIT:
            if not seen and time.monotonic() - start >= NO_RESTART:
                return True
            _settle(TICK / 1000.0)
            if ended():
                return True
            image = self._render()
            same = image == last
            last = image
            if not same:
                seen = True
            elif seen:
                return True
        return False


def _frames_of(mw: QtWidgets.QMainWindow, viewport: QtWidgets.QWidget) -> _Frames:
    """The 3D `viewport`'s frames, watched from now (_Frames); where no count shows, the renders compared are taken
    from Designer's main window `mw` (_3d_render). The 3D shot and the 3D view's set-up watch the view this way."""
    return _Frames(viewport, lambda: _3d_render(mw))


class _Waiting:
    """`with _Waiting(watched) as waiting:` around a change: on leaving, the change is waited for on `watched`, the view
    restarting and settling since a mark taken as the `with` starts (_Frames.settled). A step of the 3D view's set-up waits this
    way (scene3d.py). Inside, the step records the change once made, so an error in its wait can say it was set
    (REVIEW.md HLP-200). `waiting.needed` set False skips the wait, for a change the view takes as none (REVIEW.md
    HLP-201). An error inside skips it too. `waiting.settled` is what the wait returned, True without one (REVIEW.md
    HLP-214)."""

    def __init__(self, watched: _Frames) -> None:
        self.watched = watched
        self.needed = True
        self.settled = True
        self.since = watched.mark()

    def __enter__(self) -> '_Waiting':
        return self

    def __exit__(
        self, kind: type[BaseException] | None, error: BaseException | None, trace: TracebackType | None
    ) -> None:
        if kind is None and self.needed:
            self.settled = self.watched.settled(self.since)
