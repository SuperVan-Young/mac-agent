#!/usr/bin/env python3
"""Generate directed + random unsigned MAC vectors for mac16x16p32."""

from __future__ import annotations

import argparse
import random
from pathlib import Path


def mac_ref(a: int, b: int, c: int, acc_width: int) -> int:
    return ((a * b) + c) & ((1 << acc_width) - 1)


def directed_vectors(a_width: int, b_width: int, acc_width: int) -> list[tuple[str, int, int, int, int]]:
    a_max = (1 << a_width) - 1
    b_max = (1 << b_width) - 1
    acc_mask = (1 << acc_width) - 1
    a_hi = 1 << (a_width - 1)
    b_hi = 1 << (b_width - 1)

    directed = [
        ("DIR", 0, 0, 0),
        ("DIR", 0, b_max, acc_mask),
        ("DIR", a_max, 0, ((1 << min(acc_width, 13)) - 1) << max(acc_width - min(acc_width, 13), 0)),
        ("DIR", 1, 1, acc_mask),
        ("DIR", a_max, b_max, 0),
        ("DIR", a_max, b_max, acc_mask),
        ("DIR", a_hi, b_hi, 0),
        ("DIR", a_hi, b_hi, acc_mask),
        ("DIR", a_max >> 1, b_hi | 1, 1),
        ("DIR", (0x1234 & a_max), (0xABCD & b_max), (0xDEADBEEF & acc_mask)),
    ]
    return [(k, a, b, c, mac_ref(a, b, c, acc_width)) for (k, a, b, c) in directed]


def random_vectors(
    count: int,
    seed: int,
    a_width: int,
    b_width: int,
    acc_width: int,
) -> list[tuple[str, int, int, int, int]]:
    rng = random.Random(seed)
    vectors = []
    for _ in range(count):
        a = rng.getrandbits(a_width)
        b = rng.getrandbits(b_width)
        c = rng.getrandbits(acc_width)
        vectors.append(("RND", a, b, c, mac_ref(a, b, c, acc_width)))
    return vectors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output vector file path")
    parser.add_argument("--random-count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--a-width", type=int, default=16)
    parser.add_argument("--b-width", type=int, default=16)
    parser.add_argument("--acc-width", type=int, default=32)
    args = parser.parse_args()

    if args.random_count < 0:
        raise SystemExit("--random-count must be >= 0")
    if args.a_width <= 0 or args.b_width <= 0 or args.acc_width <= 0:
        raise SystemExit("--a-width/--b-width/--acc-width must be > 0")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    vecs = directed_vectors(args.a_width, args.b_width, args.acc_width) + random_vectors(
        args.random_count,
        args.seed,
        args.a_width,
        args.b_width,
        args.acc_width,
    )
    a_digits = max(1, (args.a_width + 3) // 4)
    b_digits = max(1, (args.b_width + 3) // 4)
    acc_digits = max(1, (args.acc_width + 3) // 4)
    with out_path.open("w", encoding="ascii") as f:
        for kind, a, b, c, exp in vecs:
            f.write(f"{kind} {a:0{a_digits}X} {b:0{b_digits}X} {c:0{acc_digits}X} {exp:0{acc_digits}X}\n")

    print(
        f"Generated {len(vecs)} vectors ({len(directed_vectors(args.a_width, args.b_width, args.acc_width))} directed + "
        f"{args.random_count} random) -> {out_path}"
    )


if __name__ == "__main__":
    main()
