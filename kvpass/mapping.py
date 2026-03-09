from __future__ import annotations

import re

# Key Vault secret name rules: 1–127 chars; allowed: 0-9 a-z A-Z -
# Поэтому кодируем всё, что не [A-Za-z0-9-], плюс "/" в "--".
_ALLOWED = re.compile(r"[A-Za-z0-9-]")


def encode_path(path: str, prefix: str) -> str:
    """
    Convert "prod/db/password" -> "kvp-prod--db--password"
    Any char outside [A-Za-z0-9-] is encoded as -xHH- (byte-wise utf-8).
    """
    if not path or path.strip() == "":
        raise ValueError("Empty path")

    # normalize slashes
    path = path.strip().strip("/")
    raw = path.replace("/", "--")

    out: list[str] = []
    for b in raw.encode("utf-8"):
        ch = chr(b)
        if _ALLOWED.fullmatch(ch):
            out.append(ch)
        else:
            out.append(f"-x{b:02x}-")
    name = prefix + "".join(out)

    if len(name) > 127:
        raise ValueError(f"Encoded name too long ({len(name)} > 127). Shorten the path.")
    return name


def decode_name(name: str, prefix: str) -> str:
    """
    Best-effort decode for display only.
    """
    if name.startswith(prefix):
        name = name[len(prefix):]

    # decode -xHH- sequences
    # We'll rebuild bytes, then decode utf-8.
    i = 0
    bytes_out = bytearray()
    while i < len(name):
        if name.startswith("-x", i):
            j = name.find("-", i + 2)
            if j != -1:
                token = name[i + 2:j]
                if len(token) == 2 and all(c in "0123456789abcdefABCDEF" for c in token):
                    bytes_out.append(int(token, 16))
                    i = j + 1
                    continue
        # normal char
        bytes_out.extend(name[i].encode("utf-8"))
        i += 1

    s = bytes(bytes_out).decode("utf-8", errors="replace")
    return s.replace("--", "/")

