"""Bounded operational sweep entry point."""

import argparse

from app.services.notifications import sweep_due_operations


def run(limit: int = 50) -> int:
    return sweep_due_operations(limit=limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deliver due notification operations")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be positive")
    print(f"Delivered {run(args.limit)} notification operation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
