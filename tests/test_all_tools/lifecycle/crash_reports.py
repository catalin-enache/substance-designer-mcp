"""Whether a Designer an agent started uploads its crash reports: Crashpad's settings in its own home (the server's
lifecycle.py: Crash reports)."""

import os
import struct

DATA = ('Library', 'Application Support', 'Adobe', 'Adobe Substance 3D Designer')
MAGIC = 0x43506473  # Crashpad's settings file ('sdPC')


def _settings(home: str) -> str:
    return os.path.join(home, *DATA, 'Sentry-Crashpad', 'settings.dat')


def uploads(home: str) -> str:
    """'on' or 'off' in the Crashpad settings of the Designer whose home is `home`, else why that can't be told."""
    path = _settings(home)
    try:
        with open(path, 'rb') as f:
            head = f.read(12)
    except OSError as e:
        return str(e)
    if len(head) < 12 or struct.unpack_from('<I', head)[0] != MAGIC:
        return "%s isn't Crashpad's settings" % path
    return 'on' if struct.unpack_from('<I', head, 8)[0] & 1 else 'off'


def uploads_on(home: str) -> None:
    """Uploads turned on in those settings, as Designer does as it starts: for a Designer the check started itself."""
    _set_uploads(home, True)


def uploads_off(home: str) -> None:
    """Uploads turned off again in those settings, where a check turned them on."""
    _set_uploads(home, False)


def _set_uploads(home: str, on: bool) -> None:
    import fcntl  # POSIX's: homes of their own are macOS's

    with open(_settings(home), 'r+b') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Crashpad's own lock
        options = struct.unpack_from('<I', f.read(12), 8)[0]
        f.seek(8)
        f.write(struct.pack('<I', (options | 1) if on else (options & ~1)))
