from __future__ import annotations

import threading
import time
import pyperclip


def copy_with_ttl(text: str, ttl_seconds: int) -> None:
    pyperclip.copy(text)

    def _clear():
        time.sleep(max(1, ttl_seconds))
        # clear only if unchanged (best effort: some clipboards may not support read)
        try:
            current = pyperclip.paste()
            if current == text:
                pyperclip.copy("")
        except Exception:
            # if paste not supported, still try to clear
            try:
                pyperclip.copy("")
            except Exception:
                pass

    t = threading.Thread(target=_clear, daemon=True)
    t.start()

