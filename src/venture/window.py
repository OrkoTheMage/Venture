from __future__ import annotations

class Window:
    """Simple terminal window renderer with a border."""

    def __init__(self, width: int = 72, height: int = 20):
        self.width = max(10, width)
        self.height = max(5, height)

    def render(self, lines: list[str]) -> None:
        # clear screen and print lines to fill the window (no border)
        print("\033[H\033[J", end="")
        # Ensure we print exactly `self.height` lines, each `self.width` chars
        content = [str(l) for l in lines]
        # Print only the provided lines (no extra bottom padding)
        for ln in content[: self.height]:
            print(ln[: self.width].ljust(self.width))

    def prompt(self, prompt: str) -> str:
        for _ in range(3):
            print()
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            raise
