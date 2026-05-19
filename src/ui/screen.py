from __future__ import annotations
import re
import sys
from collections.abc import Callable


# ── ANSI helper ───────────────────────────────────────────────────────────── #

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

def _visible_len(s: str) -> int:
    # Length of s as it appears on screen, ignoring ANSI escape codes.
    return len(_ANSI_RE.sub("", s))


# ── Screen ────────────────────────────────────────────────────────────────── #

# Owns terminal dimensions and all draw / input operations.
class Screen:

    def __init__(self, width: int = 72, height: int = 20):
        self.width  = max(10, width)
        self.height = max(5,  height)
        # Set these hooks to enable live resize during prompts.
        #   resize_check() -> bool  – returns True when a resize is pending.
        #   on_resize()             – applies the resize and repaints the
        #                             current screen.
        self.resize_check: Callable[[], bool] | None = None
        self.on_resize:    Callable[[], None] | None = None

    # ── Render ────────────────────────────────────────────────────────────── #

    def render(self, lines: list[str]) -> None:
        # Clear screen then print each line, clipped to self.width visible
        # characters and padded to fill the column (ANSI-aware).
        print("\033[H\033[J", end="")
        for ln in lines[: self.height]:
            text    = str(ln)
            visible = _ANSI_RE.sub("", text)
            if len(visible) > self.width:
                # Walk the raw string, skip ANSI sequences entirely,
                # and stop once self.width visible chars have been collected.
                count = 0
                out: list[str] = []
                i = 0
                while i < len(text):
                    m = _ANSI_RE.match(text, i)
                    if m:
                        out.append(m.group())
                        i = m.end()
                    else:
                        if count >= self.width:
                            break
                        out.append(text[i])
                        count += 1
                        i += 1
                text = "".join(out)
            pad  = max(0, self.width - _visible_len(text))
            print(" " + text + " " * pad)

    # ── Prompt / input ────────────────────────────────────────────────────── #

    def prompt(self, prompt: str, hint: str = "") -> str:
        if hint:
            print()
            print(hint)
            print()
        else:
            for _ in range(3):
                print()
        return self._read_line(prompt, hint)

    # ── Responsive readline ───────────────────────────────────────────────── #

    # Reads a line character-by-character with live resize support.
    # Polls every 50 ms via select; fires resize_check / on_resize mid-input.
    # Falls back to plain input() on Windows or when stdin is not a TTY.
    def _read_line(self, prompt: str, hint: str = "") -> str:
        try:
            import select
            import tty
            import termios
        except ImportError:
            return input(prompt)

        if not sys.stdin.isatty():
            return input(prompt)

        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf: list[str] = []

        # Reprint hint + prompt + already-typed buffer after a resize.
        def _repaint() -> None:
            if hint:
                print()
                print(hint)
                print()
            else:
                for _ in range(3):
                    print()
            print(prompt + "".join(buf), end="", flush=True)

        try:
            tty.setcbreak(fd)
            print(prompt, end="", flush=True)

            while True:
                # ── check for pending terminal resize (fires every ≤50 ms) ─ #
                if self.resize_check and self.resize_check():
                    if self.on_resize:
                        self.on_resize()
                    _repaint()

                # ── wait up to 50 ms for a keypress ──────────────────────── #
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not ready:
                    continue

                ch = sys.stdin.read(1)

                if ch in ("\n", "\r"):          # Enter
                    print()
                    return "".join(buf)

                if ch in ("\x7f", "\x08"):      # DEL / backspace
                    if buf:
                        buf.pop()
                        print("\b \b", end="", flush=True)
                    continue

                if ch == "\x03":                # Ctrl-C
                    raise KeyboardInterrupt

                if ch == "\x04":                # Ctrl-D / EOF
                    if not buf:
                        raise EOFError
                    continue

                if ch == "\x1b":                # escape sequence (arrow keys etc.)
                    r2, _, _ = select.select([sys.stdin], [], [], 0.02)
                    if r2:
                        nxt = sys.stdin.read(1)
                        if nxt == "[":
                            r3, _, _ = select.select([sys.stdin], [], [], 0.02)
                            if r3:
                                sys.stdin.read(1)
                    continue                     # silently discard

                # ── printable character ───────────────────────────────────── #
                buf.append(ch)
                print(ch, end="", flush=True)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
