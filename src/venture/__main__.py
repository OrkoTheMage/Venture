from .game import Game


def main() -> None:
    """Entry point for the `venture` console script."""
    import argparse

    parser = argparse.ArgumentParser(prog="venture", description="Play a small text adventure")
    parser.add_argument("--debug", action="store_true", help="Show debug info")
    args = parser.parse_args()

    game = Game()
    if args.debug:
        print("Starting venture (debug mode)")
    game.play()


if __name__ == "__main__":
    main()
