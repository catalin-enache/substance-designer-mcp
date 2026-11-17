"""macOS's windows, faked for the window checks' snippets (tests/test_all_tools/editor_panels_and_fit/window_states.py)
run outside Designer: Designer's main window and a window of its own under it, as _MacWindow reads them."""

from collections.abc import Sequence


class Screen:
    """Designer's main window (`main`) and the window under it (`below`): which of the two is in front, and the main
    window's look. What covers the window under it:

    - the main window in front of it, opaque;
    - with `through_covers`, the main window in front of it, transparent and click-through too;
    - with `cover`, a window the checks didn't make, above every normal window, or a locked screen: it covers both.
      `cover_after` is whether that cover is there once the main window is shown; None, as it was.

    The windows of other apps CoreGraphics lists in front of the main window (in_front_of): `ahead`, whatever is shown,
    and `late` too at its first listing, as CoreGraphics still lists the order before a show right after it (REVIEW.md
    TST-522)."""

    def __init__(
        self,
        cover: bool = False,
        through_covers: bool = False,
        cover_after: bool | None = None,
        ahead: Sequence[int] = (),
        late: Sequence[int] = (),
    ) -> None:
        self.cover = cover
        self.through_covers = through_covers
        self.cover_after = cover_after
        self.ahead = list(ahead)
        self.late = list(late)
        self.front = 'main'
        self.opaque = True
        self.main = Window(self, 'main')
        self.below = Window(self, 'below')

    def in_front_of(self, window: 'Window') -> list[int]:
        """The windows of other apps listed in front of the main window, `window` (window_states' in_front_of)."""
        late, self.late = self.late, []
        return self.ahead + late


class Window:
    """A window of `screen`, as _MacWindow reads it and changes it."""

    def __init__(self, screen: Screen, name: str) -> None:
        self.screen = screen
        self.name = name

    def show(self) -> None:
        self.screen.front = self.name
        if self.name == 'main' and self.screen.cover_after is not None:
            self.screen.cover = self.screen.cover_after

    def set_appearance(self, window: int, opacity: float, through: bool) -> None:
        self.screen.opaque = opacity == 1.0

    def windows(self, every: bool) -> list[int]:
        return [self.number()]

    def number(self) -> int:
        return 1 if self.name == 'main' else 2

    def on_screen(self, number: int) -> bool:
        return True

    def covered(self) -> bool:
        s = self.screen
        under = self.name == 'below' and s.front == 'main' and (s.opaque or s.through_covers)
        return s.cover or under
