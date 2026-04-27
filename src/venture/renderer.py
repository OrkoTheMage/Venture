from __future__ import annotations
from pathlib import Path
import time

try:
    # Python 3.9+
    from importlib.resources import files
except Exception:
    files = None


def get_ascii_lines(cols: int, rows: int) -> list[str]:
    target = "asciiLarge.txt" if cols > 82 else "asciiSmall.txt"
    asset_dir = "ascii"
    candidates = [target]
    candidates_found: list[tuple[str, list[str]]] = []
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

    return candidates_found[0][1]



