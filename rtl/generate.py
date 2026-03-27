#!/usr/bin/env python3
"""Generate a structural 16x16+32 MAC candidate netlist."""

from __future__ import annotations

from pathlib import Path


TOP = "mac16x16p32"
OUT_PATH = Path("mac16x16p32.v")
WIDTH = 32
AND2_CELL = "AND2x2_ASAP7_75t_R"
XOR2_CELL = "XOR2x2_ASAP7_75t_R"
XNOR2_CELL = "XNOR2xp5_ASAP7_75t_R"
COMPRESS_XOR2_CELL = "XOR2xp5_ASAP7_75t_R"
OUTPUT_XOR2_CELL = "XOR2xp5_ASAP7_75t_R"
AO21_CELL = "AO21x1_ASAP7_75t_R"
AOI21_CELL = "AOI21xp5_ASAP7_75t_R"
MAJ_CELL = "MAJx2_ASAP7_75t_R"
PREFIX_FAST_LO = 14
PREFIX_FAST_HI = 21
BitRef = tuple[str, int]


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

    def emit_pos_inst(self, cell: str, out: str, *ins: str) -> None:
        self.inst_counter += 1
        args = ", ".join((out, *ins))
        self.emit(f"{cell} g_{self.inst_counter}({args});")

    def logic_and(self, a: str, b: str) -> str:
        if a == self.zero or b == self.zero:
            return self.zero
        out = self.new_wire("and")
        self.emit(f"wire {out};")
        self.emit_pos_inst(AND2_CELL, out, a, b)
        return out

    def logic_inv(self, a: str) -> str:
        if a == self.zero:
            return self.zero
        out = self.new_wire("inv")
        self.emit(f"wire {out};")
        self.emit_pos_inst("INVxp33_ASAP7_75t_R", out, a)
        return out

    def logic_xor2(self, a: str, b: str, cell: str = XOR2_CELL) -> str:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        out = self.new_wire("xor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a, b)
        return out

    def logic_xnor2(self, a: str, b: str, cell: str = XNOR2_CELL) -> str:
        if a == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            return self.logic_inv(a)
        out = self.new_wire("xnor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a, b)
        return out

    def logic_ao21(self, a1: str, a2: str, b: str) -> str:
        if a1 == self.zero or a2 == self.zero:
            return b
        if b == self.zero:
            return self.logic_and(a1, a2)
        out = self.new_wire("ao21")
        self.emit(f"wire {out};")
        self.emit_pos_inst(AO21_CELL, out, a1, a2, b)
        return out

    def logic_aoi21(self, a1: str, a2: str, b: str) -> str:
        if a1 == self.zero or a2 == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            nand = self.new_wire("nand")
            self.emit(f"wire {nand};")
            self.emit_pos_inst("NAND2xp5_ASAP7_75t_R", nand, a1, a2)
            return nand
        out = self.new_wire("aoi21")
        self.emit(f"wire {out};")
        self.emit_pos_inst(AOI21_CELL, out, a1, a2, b)
        return out

    def logic_maj3(self, a: str, b: str, c: str) -> str:
        if a == self.zero:
            return self.logic_and(b, c)
        if b == self.zero:
            return self.logic_and(a, c)
        if c == self.zero:
            return self.logic_and(a, b)
        out = self.new_wire("maj")
        self.emit(f"wire {out};")
        self.emit_pos_inst(MAJ_CELL, out, a, b, c)
        return out

    def logic_xor3(self, a: str, b: str, c: str) -> str:
        return self.logic_xor2(
            self.logic_xor2(a, b, cell=COMPRESS_XOR2_CELL),
            c,
            cell=COMPRESS_XOR2_CELL,
        )

    def prefix_xor_cell(self, bit_idx: int) -> str:
        if PREFIX_FAST_LO <= bit_idx <= PREFIX_FAST_HI:
            return XOR2_CELL
        return COMPRESS_XOR2_CELL

    def half_adder(self, a: BitRef, b: BitRef) -> tuple[BitRef, BitRef]:
        a_sig, a_rank = a
        b_sig, b_rank = b
        if a_sig == self.zero:
            return b, (self.zero, -1)
        if b_sig == self.zero:
            return a, (self.zero, -1)
        base_rank = max(a_rank, b_rank)
        sum_wire = self.logic_xor2(a_sig, b_sig, cell=COMPRESS_XOR2_CELL)
        carry_wire = self.logic_and(a_sig, b_sig)
        return (sum_wire, base_rank + 2), (carry_wire, base_rank + 1)

    def full_adder(self, a: BitRef, b: BitRef, c: BitRef) -> tuple[BitRef, BitRef]:
        a_sig, a_rank = a
        b_sig, b_rank = b
        c_sig, c_rank = c
        if a_sig == self.zero:
            return self.half_adder(b, c)
        if b_sig == self.zero:
            return self.half_adder(a, c)
        if c_sig == self.zero:
            return self.half_adder(a, b)
        base_rank = max(a_rank, b_rank, c_rank)
        sum_wire = self.logic_xor3(a_sig, b_sig, c_sig)
        carry_wire = self.logic_maj3(a_sig, b_sig, c_sig)
        return (sum_wire, base_rank + 2), (carry_wire, base_rank + 1)

    def reduce_dadda(self, cols: list[list[BitRef]]) -> list[list[BitRef]]:
        max_height = max(len(col) for col in cols[:-1])
        limits = [2]
        while limits[-1] < max_height:
            limits.append((limits[-1] * 3) // 2)
        for target in reversed(limits[:-1]):
            for idx in range(len(cols) - 1):
                # Compress earlier-arriving bits first so late signals avoid
                # extra sum-stage depth when the column is over target height.
                work = sorted(cols[idx], key=lambda item: item[1])
                reduced: list[BitRef] = []
                while len(reduced) + len(work) > target:
                    excess = len(reduced) + len(work) - target
                    if excess == 1:
                        a = work.pop(0)
                        b = work.pop(0)
                        sum_wire, carry_wire = self.half_adder(a, b)
                    else:
                        a = work.pop(0)
                        b = work.pop(0)
                        c = work.pop(0)
                        sum_wire, carry_wire = self.full_adder(a, b, c)
                    reduced.append(sum_wire)
                    cols[idx + 1].append(carry_wire)
                reduced.extend(work)
                cols[idx] = sorted(reduced, key=lambda item: item[1])
        return cols

    def build(self) -> str:
        cols: list[list[BitRef]] = [[] for _ in range(WIDTH + 1)]

        self.emit(f"module {TOP}(A, B, C, D);")
        self.emit("input  [15:0] A;")
        self.emit("input  [15:0] B;")
        self.emit("input  [31:0] C;")
        self.emit("output [31:0] D;")
        self.emit(f"wire {self.zero};")
        self.emit_pos_inst(XOR2_CELL, self.zero, "A[0]", "A[0]")
        self.emit("")

        for i in range(16):
            for j in range(16):
                pp = self.new_wire("pp")
                self.emit(f"wire {pp};")
                self.emit_pos_inst(AND2_CELL, pp, f"A[{i}]", f"B[{j}]")
                cols[i + j].append((pp, 0))

        for bit in range(WIDTH):
            cols[bit].append((f"C[{bit}]", 0))

        cols = self.reduce_dadda(cols)

        self.emit("")
        row_a: list[str] = []
        row_b: list[str] = []
        for idx in range(WIDTH):
            row_a.append(cols[idx][0][0] if len(cols[idx]) >= 1 else self.zero)
            row_b.append(cols[idx][1][0] if len(cols[idx]) >= 2 else self.zero)

        bit_p: list[str] = []
        p_prev: list[str] = []
        g_prev: list[str] = []
        for idx in range(WIDTH):
            p = self.logic_xor2(row_a[idx], row_b[idx], cell=self.prefix_xor_cell(idx))
            g = self.logic_and(row_a[idx], row_b[idx])
            bit_p.append(p)
            p_prev.append(p)
            g_prev.append(g)

        for distance in (1, 2, 4, 8):
            p_next: list[str] = []
            g_next: list[str] = []
            for idx in range(WIDTH):
                if idx < distance:
                    p = p_prev[idx]
                    g = g_prev[idx]
                else:
                    p = self.logic_and(p_prev[idx], p_prev[idx - distance])
                    g = self.logic_ao21(p_prev[idx], g_prev[idx - distance], g_prev[idx])
                p_next.append(p)
                g_next.append(g)
            p_prev = p_next
            g_prev = g_next

        final_carry_bar = [self.zero] * WIDTH
        for idx in range(16, WIDTH):
            final_carry_bar[idx] = self.logic_aoi21(p_prev[idx], g_prev[idx - 16], g_prev[idx])

        self.emit("")
        for idx in range(WIDTH):
            if idx == 0:
                sum_wire = bit_p[idx]
            elif idx <= 16:
                sum_wire = self.logic_xor2(g_prev[idx - 1], bit_p[idx], cell=OUTPUT_XOR2_CELL)
            else:
                sum_wire = self.logic_xnor2(final_carry_bar[idx - 1], bit_p[idx], cell=XNOR2_CELL)
            self.emit(f"assign D[{idx}] = {sum_wire};")

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
