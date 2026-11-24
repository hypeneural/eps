from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate effective kerf/compensation from programmed and measured dimensions.")
    parser.add_argument("--programmed", type=float, required=True)
    parser.add_argument("--measured", type=float, required=True)
    args = parser.parse_args()
    delta = args.programmed - args.measured
    print(f"delta_mm={delta:.4f}")
    print(f"half_delta_mm={delta / 2:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
