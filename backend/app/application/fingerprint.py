import hashlib
from collections.abc import Sequence

SEPARATOR = "\x1f"


def fingerprint_of(parts: Sequence[str]) -> str:
    return hashlib.sha256(SEPARATOR.join(parts).encode("utf-8")).hexdigest()
