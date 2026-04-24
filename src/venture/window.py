from __future__ import annotations

class Window:
    """Simple terminal window renderer with a border."""

    def __init__(self, width: int = 72, height: int = 20, title: str | None = None):
        self.width = max(10, width)
        self.height = max(5, height)
        self.title = title

    def render(self, lines: list[str]) -> None:
        # clear screen and print lines to fill the window (no border)
        print("\033[H\033[J", end="")
        # Ensure we print exactly `self.height` lines, each `self.width` chars
        content = [str(l) for l in lines]
        # Print only the provided lines (no extra bottom padding)
        for ln in content[: self.height]:
            print(ln[: self.width].ljust(self.width))

    def pre_ascii_buffer(self) -> None:
        """Print a small vertical buffer between other prints and ASCII art."""
        for _ in range(3):
            print()

    def prompt(self, prompt: str) -> str:
        """Print a small vertical buffer before showing an input prompt, then read input."""
        self.pre_ascii_buffer()
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            raise
