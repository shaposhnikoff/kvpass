from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def edit_in_editor(initial: str) -> str:
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        raise SystemExit("Set $EDITOR (e.g. export EDITOR=nano / vim)")

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "secret.txt"
        p.write_text(initial, encoding="utf-8")
        subprocess.run([editor, str(p)], check=False)
        return p.read_text(encoding="utf-8").rstrip("\n")
