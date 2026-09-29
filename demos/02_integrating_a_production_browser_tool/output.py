"""Printing: every line starts with a tag for the part of the loop it comes from. Colors show in a terminal.

Every line also goes into a run record in runs/.
"""

import os
import sys
import time
from pathlib import Path

COLORS = {"browser": "90", "session": "35", "thinking": "36", "claude": "1;36", "result": "37", "blocked": "1;31", "refused": "1;31",
          "verify": "32", "step": "1;35", "stopped": "33"}
RUN_RECORD = Path(__file__).parent / "runs" / f"{time.strftime('%Y-%m-%d_%H%M%S')}.log"


def tagged(tag, text):
    label = f"[{tag}]".ljust(11)
    body = str(text).strip().replace("\n", "\n" + " " * 11)
    RUN_RECORD.parent.mkdir(exist_ok=True)
    with RUN_RECORD.open("a") as record:
        record.write(f"{time.strftime('%H:%M:%S')} {label}{body}\n")
    if sys.stdout.isatty() and "NO_COLOR" not in os.environ:
        label = f"\033[{COLORS[tag]}m{label}\033[0m"
    return label + body
