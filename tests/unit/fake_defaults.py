"""A fake of macOS's `defaults` for designer_preferences.run_defaults, which conftest gives every unit test so none reads
or writes the user's real preferences: one domain held here, as the real one behaves on it (measured 2026-11-13, a
scratch domain): `export DOMAIN -` prints it as a plist, an empty one if it was never written; `delete DOMAIN KEY` fails
on a key not there; `import DOMAIN FILE` merges, keeping keys not in the file. Also lock_held(), whether a save or a
put-back holds designer_preferences' lock."""

import plistlib
from pathlib import Path

import designer_preferences


class FakeDefaults:
    """`domain` is the file's content; `calls` every call's arguments; `fail` a verb's error, raised as the real
    run_defaults raises one; `lossy` an import that leaves out one of the file's keys. `users_data` is the user's
    Designer's data folder, where a test writes their log; `plist` where the file itself is (designer_preferences.
    plist_file), not there unless a test writes it."""

    def __init__(self, users_data: Path, preferences: Path) -> None:
        self.domain: dict[str, object] = {}
        self.calls: list[tuple[str, ...]] = []
        self.fail: dict[str, str] = {}
        self.lossy = False
        self.users_data = users_data
        self.plist = preferences / ('%s.plist' % designer_preferences.DOMAIN)

    def __call__(self, *args: str) -> bytes:
        self.calls.append(args)
        verb = args[0]
        assert args[1] == designer_preferences.DOMAIN, args
        if verb in self.fail:
            raise designer_preferences.PreferencesError(self.fail[verb])
        if verb == 'export':
            assert args[2:] == ('-',), args
            return plistlib.dumps(self.domain, fmt=plistlib.FMT_XML)
        if verb == 'delete':
            if args[2] not in self.domain:
                raise designer_preferences.PreferencesError('Domain (%s) not found.' % args[1])
            del self.domain[args[2]]
            return b''
        if verb == 'import':
            imported = plistlib.loads(Path(args[2]).read_bytes())
            if self.lossy:
                imported.pop(sorted(imported)[0])
            self.domain.update(imported)
            return b''
        raise AssertionError('defaults %s is not used' % verb)

    def verbs(self) -> list[str]:
        """The verbs called, in order."""
        return [call[0] for call in self.calls]


def lock_held() -> bool:
    """Whether designer_preferences' lock is held: another open file can't take it."""
    import fcntl  # POSIX (REVIEW.md TST-356)

    with open(designer_preferences.lock_file(), 'a') as other:
        try:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False
