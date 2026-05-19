from __future__ import annotations

import sys


class Window:
    """Simple terminal window renderer with a border."""

    def __init__(self, width: int = 72, height: int = 20):
        self.width  = max(10, width)
        self.height = max(5,  height)
        # Set these hooks to enable live resize during prompts.
        #   resize_check() -> bool  – returns True when a resize is pending.
        #   on_resize()             – applies the resize and repaints the
        #                             current screen.
        self.resize_check = None   # type: ignore[assignment]
        self.on_resize    = None   # type: ignore[assignment]

    def render(self, lines: list[str]) -> None:
        # Clear screen then print lines, each clipped/padded to self.width.
        print("\033[H\033[J", end="")
        content = [str(l) for l in lines]
        for ln in content[: self.height]:
            print(ln[: self.width].ljust(self.width))

    def prompt(self, prompt: str, hint: str = "") -> str:
        if hint:
            print()
            print(hint)
            print()
        else:
            for _ in range(3):
                print()
        return self._read_line(prompt, hint)

    # ── responsive readline ──────────────────────────────────────────────── #

    def _read_line(self, prompt: str, hint: str = "") -> str:
        """Read a line from stdin with live terminal-resize support.

        While blocked waiting for input the loop polls every 50 ms.  When a
        resize is pending (``resize_check`` returns True) ``on_resize`` is
        called to repaint the current screen at the new dimensions, then the
        hint block and prompt are reprinted so the user can continue typing
        without interruption.

        Falls back to plain ``input()`` on Windows or when stdin is not a TTY.
        """
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

        def _repaint() -> None:
            """Reprint hint + prompt + already-typed buffer after a resize."""
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
                        self.on_resize()   # redraws current screen at new size
                    _repaint()             # restore hint + prompt + typed chars

                # ── wait up to 50 ms for a keypress ────────────────────── #
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
                                sys.stdin.read(1)   # direction / modifier char
                    continue                     # silently discard

                # ── printable character ─────────────────────────────────── #
                buf.append(ch)
                print(ch, end="", flush=True)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
