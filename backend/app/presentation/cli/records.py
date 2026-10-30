import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

YEN_PER_DOLLAR = 150
LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def label(text: str) -> str:
    if not LABEL.fullmatch(text):
        raise argparse.ArgumentTypeError("英数字と . _ - だけで、英数字から始めてください")
    return text


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]


def current_commit() -> str | None:
    here = Path(__file__).resolve().parent
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=here, capture_output=True, check=True
        ).stdout
        changes = subprocess.run(
            ["git", "diff", "HEAD"], cwd=here, capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"commit を記録できません(結果の commit は null): {error}", file=sys.stderr)
        return None
    commit = head.decode().strip()
    return f"{commit}-dirty-{digest(changes)}" if changes else commit


def reserve(out: Path, paths: Sequence[Path]) -> None:
    reserved: list[Path] = []
    try:
        out.mkdir(parents=True, exist_ok=True)
        for path in paths:
            path.touch(exist_ok=False)
            reserved.append(path)
    except OSError as error:
        for path in reserved:
            path.unlink(missing_ok=True)
        sys.exit(f"結果を書く場所を作れません: {error}")
