from pathlib import Path
import json


def state_path() -> Path:
    return Path.home() / ".venture_state.json"


def load_state() -> dict:
    p = state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    p = state_path()
    try:
        p.write_text(json.dumps(state))
    except Exception:
        pass


def clear_state() -> None:
    p = state_path()
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass
