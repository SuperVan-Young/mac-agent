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
XNOR2_FAST_CELL = "XNOR2x2_ASAP7_75t_R"
COMPRESS_XOR2_CELL = "XOR2xp5_ASAP7_75t_R"
COMPRESS_FAST_XOR2_CELL = "XOR2x2_ASAP7_75t_R"
OUTPUT_XOR2_CELL = "XOR2xp5_ASAP7_75t_R"
AO21_CELL = "AO21x1_ASAP7_75t_R"
AOI21_CELL = "AOI21xp5_ASAP7_75t_R"
MAJ_CELL = "MAJx2_ASAP7_75t_R"
NOR2_CELL = "NOR2xp33_ASAP7_75t_R"
PREFIX_FAST_LO = 14
PREFIX_FAST_HI = 21
COMPRESS_FAST_LO = 14
COMPRESS_FAST_HI = 20
MIXED_HIGH_LO = 18
MIXED_HIGH_HI = 31
BitRef = tuple[str, int]
PhasedBitRef = tuple[str, int, bool]


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

    def logic_nor(self, a: str, b: str) -> str:
        if a == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            return self.logic_inv(a)
        out = self.new_wire("nor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(NOR2_CELL, out, a, b)
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

    def mixed_half_adder(self, a: str, b: str) -> tuple[str, str]:
        carry_bar = self.new_wire("ha_cbar")
        sum_bar = self.new_wire("ha_sbar")
        self.emit(f"wire {carry_bar};")
        self.emit(f"wire {sum_bar};")
        # HAxp5 emits complemented carry and complemented parity.
        self.emit_pos_inst("HAxp5_ASAP7_75t_R", carry_bar, sum_bar, a, b)
        return sum_bar, carry_bar

    def mixed_full_adder(self, a: str, b: str, c: str) -> tuple[str, str]:
        carry_bar = self.new_wire("fa_cbar")
        sum_bar = self.new_wire("fa_sbar")
        self.emit(f"wire {carry_bar};")
        self.emit(f"wire {sum_bar};")
        # FAx1 emits complemented carry and complemented parity.
        self.emit_pos_inst("FAx1_ASAP7_75t_R", carry_bar, sum_bar, a, b, c)
        return sum_bar, carry_bar

    def materialize_positive(self, bit: PhasedBitRef) -> PhasedBitRef:
        sig, rank, inverted = bit
        if not inverted or sig == self.zero:
            return bit
        return (self.logic_inv(sig), rank + 1, False)

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

    def prefix_xnor_cell(self, bit_idx: int) -> str:
        if PREFIX_FAST_LO <= bit_idx <= PREFIX_FAST_HI:
            return XNOR2_FAST_CELL
        return XNOR2_CELL

    def compress_xor_cell(self, bit_idx: int) -> str:
        if COMPRESS_FAST_LO <= bit_idx <= COMPRESS_FAST_HI:
            return COMPRESS_FAST_XOR2_CELL
        return COMPRESS_XOR2_CELL

    def compress_first_xor_cell(self, bit_idx: int) -> str:
        # Keep the first XOR in the FA on the smaller cell and only spend
        # faster XORs on the second-stage sum combine within the D18 window.
        return COMPRESS_XOR2_CELL

    def half_adder(
        self, a: PhasedBitRef, b: PhasedBitRef, bit_idx: int
    ) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        if a_sig == self.zero:
            return (b_sig, b_rank, False), (self.zero, -1, False)
        if b_sig == self.zero:
            return (a_sig, a_rank, False), (self.zero, -1, False)
        base_rank = max(a_rank, b_rank)
        sum_wire = self.logic_xor2(a_sig, b_sig, cell=self.compress_xor_cell(bit_idx))
        carry_wire = self.logic_and(a_sig, b_sig)
        return (sum_wire, base_rank + 2, False), (carry_wire, base_rank + 1, False)

    def full_adder(
        self, a: PhasedBitRef, b: PhasedBitRef, c: PhasedBitRef, bit_idx: int
    ) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        c_sig, c_rank, _ = self.materialize_positive(c)
        if a_sig == self.zero:
            return self.half_adder(b, c, bit_idx)
        if b_sig == self.zero:
            return self.half_adder(a, c, bit_idx)
        if c_sig == self.zero:
            return self.half_adder(a, b, bit_idx)
        base_rank = max(a_rank, b_rank, c_rank)
        xor_ab = self.logic_xor2(a_sig, b_sig, cell=self.compress_first_xor_cell(bit_idx))
        sum_wire = self.logic_xor2(xor_ab, c_sig, cell=self.compress_xor_cell(bit_idx))
        carry_wire = self.logic_maj3(a_sig, b_sig, c_sig)
        return (sum_wire, base_rank + 2, False), (carry_wire, base_rank + 1, False)

    def mixed_stage_half_adder(self, a: PhasedBitRef, b: PhasedBitRef) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        base_rank = max(a_rank, b_rank)
        sum_bar, carry_bar = self.mixed_half_adder(a_sig, b_sig)
        return (sum_bar, base_rank + 2, True), (carry_bar, base_rank + 1, True)

    def mixed_stage_full_adder(self, a: PhasedBitRef, b: PhasedBitRef, c: PhasedBitRef) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        c_sig, c_rank, _ = self.materialize_positive(c)
        base_rank = max(a_rank, b_rank, c_rank)
        sum_bar, carry_bar = self.mixed_full_adder(a_sig, b_sig, c_sig)
        return (sum_bar, base_rank + 2, True), (carry_bar, base_rank + 1, True)

    def reduce_dadda(self, cols: list[list[PhasedBitRef]]) -> list[list[PhasedBitRef]]:
        max_height = max(len(col) for col in cols[:-1])
        limits = [2]
        while limits[-1] < max_height:
            limits.append((limits[-1] * 3) // 2)
        for target in reversed(limits[:-1]):
            for idx in range(len(cols) - 1):
                # Compress earlier-arriving bits first so late signals avoid
                # extra sum-stage depth when the column is over target height.
                work = sorted(cols[idx], key=lambda item: item[1])
                reduced: list[PhasedBitRef] = []
                while len(reduced) + len(work) > target:
                    excess = len(reduced) + len(work) - target
                    use_mixed = target == 2 and (idx < 12 or MIXED_HIGH_LO <= idx <= MIXED_HIGH_HI)
                    if excess == 1:
                        a = work.pop(0)
                        b = work.pop(0)
                        if use_mixed:
                            sum_wire, carry_wire = self.mixed_stage_half_adder(a, b)
                        else:
                            sum_wire, carry_wire = self.half_adder(a, b, idx)
                    else:
                        a = work.pop(0)
                        b = work.pop(0)
                        c = work.pop(0)
                        if use_mixed:
                            sum_wire, carry_wire = self.mixed_stage_full_adder(a, b, c)
                        else:
                            sum_wire, carry_wire = self.full_adder(a, b, c, idx)
                    reduced.append(sum_wire)
                    cols[idx + 1].append(carry_wire)
                reduced.extend(work)
                cols[idx] = sorted(reduced, key=lambda item: item[1])
        return cols

    def build(self) -> str:
        cols: list[list[PhasedBitRef]] = [[] for _ in range(WIDTH + 1)]

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
                cols[i + j].append((pp, 0, False))

        for bit in range(WIDTH):
            cols[bit].append((f"C[{bit}]", 0, False))

        cols = self.reduce_dadda(cols)

        self.emit("")
        row_a_bits: list[PhasedBitRef] = []
        row_b_bits: list[PhasedBitRef] = []
        for idx in range(WIDTH):
            if len(cols[idx]) >= 1:
                row_a_bits.append(cols[idx][0])
            else:
                row_a_bits.append((self.zero, -1, False))
            if len(cols[idx]) >= 2:
                row_b_bits.append(cols[idx][1])
            else:
                row_b_bits.append((self.zero, -1, False))

        bit_p: list[str] = []
        p_prev: list[str] = []
        g_prev: list[str] = []
        top_sum_sig = self.zero
        top_sum_use_xor = False
        for idx in range(WIDTH - 1):
            a_sig, _, a_inv = row_a_bits[idx]
            b_sig, _, b_inv = row_b_bits[idx]
            if a_sig == self.zero or b_sig == self.zero:
                a_sig, _, _ = self.materialize_positive(row_a_bits[idx])
                b_sig, _, _ = self.materialize_positive(row_b_bits[idx])
                p = self.logic_xor2(a_sig, b_sig, cell=self.prefix_xor_cell(idx))
                g = self.logic_and(a_sig, b_sig)
            elif a_inv == b_inv:
                p = self.logic_xor2(a_sig, b_sig, cell=self.prefix_xor_cell(idx))
                if a_inv:
                    g = self.logic_nor(a_sig, b_sig)
                else:
                    g = self.logic_and(a_sig, b_sig)
            else:
                # Opposite-polarity survivors preserve parity via XNOR.
                p = self.logic_xnor2(a_sig, b_sig, cell=self.prefix_xnor_cell(idx))
                a_pos, _, _ = self.materialize_positive(row_a_bits[idx])
                b_pos, _, _ = self.materialize_positive(row_b_bits[idx])
                g = self.logic_and(a_pos, b_pos)
            bit_p.append(p)
            p_prev.append(p)
            g_prev.append(g)

        a_sig, _, a_inv = row_a_bits[WIDTH - 1]
        b_sig, _, b_inv = row_b_bits[WIDTH - 1]
        if a_sig == self.zero or b_sig == self.zero:
            a_sig, _, _ = self.materialize_positive(row_a_bits[WIDTH - 1])
            b_sig, _, _ = self.materialize_positive(row_b_bits[WIDTH - 1])
            top_sum_sig = self.logic_xor2(a_sig, b_sig, cell=OUTPUT_XOR2_CELL)
        elif a_inv == b_inv:
            top_sum_sig = self.logic_xor2(a_sig, b_sig, cell=OUTPUT_XOR2_CELL)
        else:
            # D[31] only needs the incoming carry from bit 30, so keep the
            # local parity complemented and consume it directly with XOR.
            top_sum_sig = self.logic_xor2(a_sig, b_sig, cell=OUTPUT_XOR2_CELL)
            top_sum_use_xor = True

        for distance in (1, 2, 4, 8):
            p_next: list[str] = []
            g_next: list[str] = []
            for idx in range(WIDTH - 1):
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
        for idx in range(16, WIDTH - 1):
            final_carry_bar[idx] = self.logic_aoi21(p_prev[idx], g_prev[idx - 16], g_prev[idx])

        self.emit("")
        for idx in range(WIDTH - 1):
            if idx == 0:
                sum_wire = bit_p[idx]
            elif idx <= 16:
                sum_wire = self.logic_xor2(g_prev[idx - 1], bit_p[idx], cell=OUTPUT_XOR2_CELL)
            else:
                sum_wire = self.logic_xnor2(final_carry_bar[idx - 1], bit_p[idx], cell=XNOR2_CELL)
            self.emit(f"assign D[{idx}] = {sum_wire};")
        if top_sum_use_xor:
            sum_wire = self.logic_xor2(final_carry_bar[WIDTH - 2], top_sum_sig, cell=OUTPUT_XOR2_CELL)
        else:
            sum_wire = self.logic_xnor2(final_carry_bar[WIDTH - 2], top_sum_sig, cell=XNOR2_CELL)
        self.emit(f"assign D[{WIDTH - 1}] = {sum_wire};")

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
