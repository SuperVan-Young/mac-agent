#!/usr/bin/env python3
"""Generate directed + random unsigned MAC vectors for mac16x16p32."""

from __future__ import annotations

import argparse
import random
from pathlib import Path


def mac_ref(a: int, b: int, c: int) -> int:
    return ((a * b) + c) & 0xFFFFFFFF


def directed_vectors() -> list[tuple[str, int, int, int, int]]:
    directed = [
        ("DIR", 0x0000, 0x0000, 0x00000000),
        ("DIR", 0x0000, 0xFFFF, 0xFFFFFFFF),
        ("DIR", 0xFFFF, 0x0000, 0x12345678),
        ("DIR", 0x0001, 0x0001, 0xFFFFFFFF),
        ("DIR", 0xFFFF, 0xFFFF, 0x00000000),
        ("DIR", 0xFFFF, 0xFFFF, 0xFFFFFFFF),
        ("DIR", 0x8000, 0x8000, 0x00000000),
        ("DIR", 0x8000, 0x8000, 0xFFFFFFFF),
        ("DIR", 0x7FFF, 0x8001, 0x00000001),
        ("DIR", 0x1234, 0xABCD, 0xDEADBEEF),
    ]
    return [(k, a, b, c, mac_ref(a, b, c)) for (k, a, b, c) in directed]


def random_vectors(count: int, seed: int) -> list[tuple[str, int, int, int, int]]:
    rng = random.Random(seed)
    vectors = []
    for _ in range(count):
        a = rng.getrandbits(16)
        b = rng.getrandbits(16)
        c = rng.getrandbits(32)
        vectors.append(("RND", a, b, c, mac_ref(a, b, c)))
    return vectors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output vector file path")
    parser.add_argument("--random-count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    if args.random_count < 0:
        raise SystemExit("--random-count must be >= 0")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    vecs = directed_vectors() + random_vectors(args.random_count, args.seed)
    with out_path.open("w", encoding="ascii") as f:
        for kind, a, b, c, exp in vecs:
            f.write(f"{kind} {a:04X} {b:04X} {c:08X} {exp:08X}\n")

    print(
        f"Generated {len(vecs)} vectors ({len(directed_vectors())} directed + "
        f"{args.random_count} random) -> {out_path}"
    )


if __name__ == "__main__":
    main()
