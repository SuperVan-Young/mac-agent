#!/usr/bin/env python3
"""Generate a structural 16x16+32 MAC candidate netlist.

The emitted top module avoids behavioral arithmetic operators in the top-level
body and is built from explicit bitwise logic equations plus output buffers.
"""

from __future__ import annotations

from pathlib import Path


TOP = "mac16x16p32"
OUT_PATH = Path("mac16x16p32.v")
WIDTH = 32


class NetlistBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.counter = 0
        self.inst_counter = 0
        self.zero = "const0"

    def new_wire(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}_{self.counter}"

    def emit(self, line: str = "") -> None:
        self.lines.append(line)

    def emit_inst(self, cell: str, out: str, *ins: str) -> None:
        self.inst_counter += 1
        args = ", ".join((out, *ins))
        self.emit(f"{cell} g_{self.inst_counter}({args});")

    def logic_and(self, a: str, b: str) -> str:
        if a == self.zero or b == self.zero:
            return self.zero
        out = self.new_wire("and")
        self.emit(f"wire {out};")
        self.emit_inst("AND2x4_ASAP7_75t_R", out, a, b)
        return out

    def logic_or(self, a: str, b: str) -> str:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        out = self.new_wire("or")
        self.emit(f"wire {out};")
        self.emit_inst("OR2x4_ASAP7_75t_R", out, a, b)
        return out

    def logic_xor2(self, a: str, b: str) -> str:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        out = self.new_wire("xor")
        self.emit(f"wire {out};")
        self.emit_inst("XOR2x2_ASAP7_75t_R", out, a, b)
        return out

    def logic_xor3(self, a: str, b: str, c: str) -> str:
        return self.logic_xor2(self.logic_xor2(a, b), c)

    def full_adder(self, a: str, b: str, c: str) -> tuple[str, str]:
        sum_wire = self.logic_xor3(a, b, c)
        ab = self.logic_and(a, b)
        ac = self.logic_and(a, c)
        bc = self.logic_and(b, c)
        carry_wire = self.logic_or(self.logic_or(ab, ac), bc)
        return sum_wire, carry_wire

    def build(self) -> str:
        cols: list[list[str]] = [[] for _ in range(WIDTH + 2)]

        self.emit(f"module {TOP}(A, B, C, D);")
        self.emit("input  [15:0] A;")
        self.emit("input  [15:0] B;")
        self.emit("input  [31:0] C;")
        self.emit("output [31:0] D;")
        self.emit(f"wire {self.zero};")
        self.emit_inst("XOR2x2_ASAP7_75t_R", self.zero, "A[0]", "A[0]")
        self.emit("")

        for i in range(16):
            for j in range(16):
                pp = self.new_wire("pp")
                self.emit(f"wire {pp};")
                self.emit_inst("AND2x4_ASAP7_75t_R", pp, f"A[{i}]", f"B[{j}]")
                cols[i + j].append(pp)

        for bit in range(WIDTH):
            cols[bit].append(f"C[{bit}]")

        stage = 0
        while any(len(col) > 2 for col in cols[:-1]):
            next_cols: list[list[str]] = [[] for _ in range(WIDTH + 2)]
            for idx, bits in enumerate(cols[:-1]):
                work = bits[:]
                while len(work) >= 3:
                    stage += 1
                    a = work.pop(0)
                    b = work.pop(0)
                    c = work.pop(0)
                    sum_wire, carry_wire = self.full_adder(a, b, c)
                    next_cols[idx].append(sum_wire)
                    next_cols[idx + 1].append(carry_wire)
                if len(work) == 2:
                    next_cols[idx].extend(work)
                elif len(work) == 1:
                    next_cols[idx].append(work[0])
            next_cols[-1].extend(cols[-1])
            cols = next_cols

        self.emit("")
        row_a: list[str] = []
        row_b: list[str] = []
        for idx in range(WIDTH):
            if len(cols[idx]) >= 1:
                row_a.append(cols[idx][0])
            else:
                row_a.append(self.zero)
            if len(cols[idx]) >= 2:
                row_b.append(cols[idx][1])
            else:
                row_b.append(self.zero)

        p_prev: list[str] = []
        g_prev: list[str] = []
        for idx in range(WIDTH):
            p = self.logic_xor2(row_a[idx], row_b[idx])
            g = self.logic_and(row_a[idx], row_b[idx])
            p_prev.append(p)
            g_prev.append(g)

        for distance in (1, 2, 4, 8, 16):
            p_next: list[str] = []
            g_next: list[str] = []
            for idx in range(WIDTH):
                if idx < distance:
                    p = p_prev[idx]
                    g = g_prev[idx]
                else:
                    p = self.logic_and(p_prev[idx], p_prev[idx - distance])
                    g = self.logic_or(g_prev[idx], self.logic_and(p_prev[idx], g_prev[idx - distance]))
                p_next.append(p)
                g_next.append(g)
            p_prev = p_next
            g_prev = g_next

        carries = [self.zero]
        for idx in range(1, WIDTH):
            carries.append(g_prev[idx - 1])

        self.emit("")
        for idx in range(WIDTH):
            sum_wire = self.logic_xor3(carries[idx], row_a[idx], row_b[idx])
            self.emit_inst("BUFx4_ASAP7_75t_R", f"D[{idx}]", sum_wire)

        self.emit("endmodule")
        self.emit("")
        return "\n".join(self.lines)


def main() -> int:
    netlist = NetlistBuilder().build()
    OUT_PATH.write_text(netlist, encoding="utf-8")
    print(f"generated {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
