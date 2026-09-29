"""Console output for the local entry points.

On Windows, output that is piped or redirected is encoded with the system
code page, which cannot represent the receipt frame or the dashes in the
event text. Entry points call ``use_utf8_output`` once before printing.
"""

from __future__ import annotations

import sys


def use_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
