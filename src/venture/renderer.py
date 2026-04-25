from __future__ import annotations
from pathlib import Path
import time

try:
    # Python 3.9+
    from importlib.resources import files
except Exception:
    files = None


def get_ascii_lines(cols: int, rows: int) -> list[str]:
    # Selection rules copied from original game logic
    if cols >= 130 and rows >= 58:
        candidates = ["asciiLarge.txt", "asciiMed.txt", "asciiSmall.txt", "ascii.txt"]
    elif cols <= 80 and rows <= 30:
        candidates = ["asciiSmall.txt", "asciiMed.txt", "asciiLarge.txt", "ascii.txt"]
    elif cols <= 100 and rows <= 30:
        candidates = ["asciiMed.txt", "asciiSmall.txt", "asciiLarge.txt", "ascii.txt"]
    else:
        candidates = ["asciiMed.txt", "asciiLarge.txt", "asciiSmall.txt", "ascii.txt"]

    candidates_found: list[tuple[str, list[str]]] = []
    small_category = cols <= 80 and rows <= 30
    asset_dir = "ascii"
    for name in candidates:
        lines = None
        try:
            cwd_path = Path.cwd() / name
            if cwd_path.exists():
                lines = cwd_path.read_text().splitlines()
            else:
                cwd_path2 = Path.cwd() / asset_dir / name
                if cwd_path2.exists():
                    lines = cwd_path2.read_text().splitlines()
                else:
                    local_path = Path(__file__).resolve().parent / name
                    if local_path.exists():
                        lines = local_path.read_text().splitlines()
                    else:
                        local_path2 = Path(__file__).resolve().parent / asset_dir / name
                        if local_path2.exists():
                            lines = local_path2.read_text().splitlines()
        except Exception:
            lines = None

        if lines is None and files is not None and __package__:
            try:
                try:
                    res = files(__package__).joinpath(name)
                    txt = res.read_text()
                    lines = txt.splitlines()
                except Exception:
                    res2 = files(__package__).joinpath(asset_dir).joinpath(name)
                    txt = res2.read_text()
                    lines = txt.splitlines()
            except Exception:
                lines = None

        if lines:
            candidates_found.append((name, lines))

    if not candidates_found:
        return []

    if small_category:
        for name, lines in candidates_found:
            if name == "asciiSmall.txt":
                return lines

    for name, lines in candidates_found:
        max_len = max((len(l) for l in lines), default=0)
        cnt = len(lines)
        if max_len <= cols and cnt <= rows:
            return lines

    for name, lines in candidates_found:
        max_len = max((len(l) for l in lines), default=0)
        if max_len <= cols:
            return lines

    best = min(candidates_found, key=lambda nl: max((len(l) for l in nl[1]), default=0))
    return best[1]



