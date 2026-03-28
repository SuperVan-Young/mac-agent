#!/usr/bin/env python3
"""Generate a structural 16x16+32 MAC candidate netlist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


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
AO21_FAST_CELL = "AO21x2_ASAP7_75t_R"
AOI21_CELL = "AOI21xp5_ASAP7_75t_R"
FINAL_CARRY_STRONG_AOI21_CELL = "AOI21x1_ASAP7_75t_R"
MAJ_CELL = "MAJx2_ASAP7_75t_R"
NOR2_CELL = "NOR2xp33_ASAP7_75t_R"
PREFIX_FAST_LO = 14
PREFIX_FAST_HI = 21
COMPRESS_FAST_LO = 12
COMPRESS_FAST_HI = 30
MIXED_HIGH_LO = 16
MIXED_HIGH_HI = 31
AGGRESSIVE_COMPRESS_LO = 18
AGGRESSIVE_COMPRESS_HI = 30
HOT_SUFFIX_CANDIDATE_LO = 22
HOT_SUFFIX_TOP_K = 4
DEFAULT_INPUT_SLEW = 10.0
DEFAULT_OUTPUT_LOAD = 4.0
LIBERTY_PATHS = (
    Path("tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib"),
    Path("tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib"),
    Path("tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib"),
)
MODELED_CELLS = {
    AND2_CELL,
    "AND2x4_ASAP7_75t_R",
    XOR2_CELL,
    COMPRESS_XOR2_CELL,
    XNOR2_CELL,
    XNOR2_FAST_CELL,
    AO21_CELL,
    "AO21x2_ASAP7_75t_R",
    AOI21_CELL,
    FINAL_CARRY_STRONG_AOI21_CELL,
    MAJ_CELL,
    NOR2_CELL,
    "INVxp33_ASAP7_75t_R",
    "NAND2xp5_ASAP7_75t_R",
    "FAx1_ASAP7_75t_R",
    "HAxp5_ASAP7_75t_R",
}
BitRef = tuple[str, int]
PhasedBitRef = tuple[str, int, bool]


@dataclass(frozen=True)
class TimingState:
    arrival: float
    slew: float


@dataclass(frozen=True)
class TableModel:
    index_1: tuple[float, ...]
    index_2: tuple[float, ...]
    values: tuple[tuple[float, ...], ...]

    def lookup(self, slew: float, load: float) -> float:
        def bound(indices: tuple[float, ...], value: float) -> tuple[int, int, float]:
            if len(indices) == 1:
                return 0, 0, 0.0
            if value <= indices[0]:
                return 0, 0, 0.0
            if value >= indices[-1]:
                return len(indices) - 1, len(indices) - 1, 0.0
            for idx in range(len(indices) - 1):
                lo = indices[idx]
                hi = indices[idx + 1]
                if lo <= value <= hi:
                    span = hi - lo
                    frac = 0.0 if span == 0.0 else (value - lo) / span
                    return idx, idx + 1, frac
            return len(indices) - 1, len(indices) - 1, 0.0

        i0, i1, fi = bound(self.index_1, slew)
        j0, j1, fj = bound(self.index_2, load)
        v00 = self.values[i0][j0]
        v01 = self.values[i0][j1]
        v10 = self.values[i1][j0]
        v11 = self.values[i1][j1]
        row0 = v00 + (v01 - v00) * fj
        row1 = v10 + (v11 - v10) * fj
        return row0 + (row1 - row0) * fi


@dataclass(frozen=True)
class ArcModel:
    delay: TableModel
    transition: TableModel


@dataclass
class CellModel:
    input_caps: dict[str, float]
    arcs: dict[tuple[str, str], ArcModel]


@dataclass(frozen=True)
class CompressorOp:
    kind: str
    column: int
    use_mixed: bool
    inputs: tuple[str, ...]
    sum_out: str
    carry_out: str


@dataclass(frozen=True)
class CompressorStage:
    target: int
    operations: tuple[CompressorOp, ...]


@dataclass(frozen=True)
class CompressorTreeIR:
    stages: tuple[CompressorStage, ...]
    outputs: tuple[tuple[PhasedBitRef, ...], ...]


@dataclass(frozen=True)
class PhaseOption:
    bit: PhasedBitRef
    inv_cost: int


@dataclass(frozen=True)
class PhaseOptions:
    positive: PhaseOption
    negative: PhaseOption


@dataclass(frozen=True)
class PhasePlan:
    arrival: float
    inv_cost: int
    lhs: PhaseOption
    rhs: PhaseOption
    gate_kind: str
    want_inverted: bool


class LibertyTimingModel:
    def __init__(self, liberty_paths: tuple[Path, ...], modeled_cells: set[str]) -> None:
        self.cells: dict[str, CellModel] = {}
        for path in liberty_paths:
            if path.exists():
                self._parse_file(path, modeled_cells)

    def input_cap(self, cell: str, pin: str) -> float:
        return self.cells.get(cell, CellModel({}, {})).input_caps.get(pin, DEFAULT_OUTPUT_LOAD)

    def propagate(
        self,
        cell: str,
        out_pin: str,
        pin_states: dict[str, TimingState],
        load: float = DEFAULT_OUTPUT_LOAD,
    ) -> TimingState:
        model = self.cells.get(cell)
        if model is None:
            base = max((state.arrival for state in pin_states.values()), default=0.0)
            slew = max((state.slew for state in pin_states.values()), default=DEFAULT_INPUT_SLEW)
            return TimingState(base + 30.0, slew + 8.0)
        arrival = 0.0
        slew = 0.0
        for pin_name, state in pin_states.items():
            arc = model.arcs.get((out_pin, pin_name))
            if arc is None:
                continue
            arc_delay = arc.delay.lookup(state.slew, load)
            arrival = max(arrival, state.arrival + arc_delay)
            slew = max(slew, arc.transition.lookup(state.slew, load))
        if arrival == 0.0 and pin_states:
            arrival = max(state.arrival for state in pin_states.values())
        if slew == 0.0 and pin_states:
            slew = max(state.slew for state in pin_states.values())
        return TimingState(arrival, slew)

    def _parse_file(self, path: Path, modeled_cells: set[str]) -> None:
        text = path.read_text(encoding="utf-8")
        for cell_name in modeled_cells:
            if cell_name in self.cells:
                continue
            marker = f"cell ({cell_name})"
            start = text.find(marker)
            if start < 0:
                continue
            cell_block = self._extract_block(text, start)
            self.cells[cell_name] = self._parse_cell(cell_block)

    def _parse_cell(self, cell_block: str) -> CellModel:
        input_caps: dict[str, float] = {}
        arcs: dict[tuple[str, str], ArcModel] = {}
        pos = 0
        while True:
            pin_start = cell_block.find("pin (", pos)
            if pin_start < 0:
                break
            pin_block = self._extract_block(cell_block, pin_start)
            pin_name = pin_block[pin_block.find("(") + 1 : pin_block.find(")")].strip()
            pos = pin_start + len(pin_block)
            direction_match = re.search(r"direction\s*:\s*([a-z_]+)\s*;", pin_block)
            if direction_match is None:
                continue
            direction = direction_match.group(1)
            if direction == "input":
                caps = [float(val) for val in re.findall(r"capacitance\s*:\s*([0-9.]+)\s*;", pin_block)]
                if caps:
                    input_caps[pin_name] = max(caps)
                continue
            if direction != "output":
                continue
            timing_pos = 0
            while True:
                timing_start = pin_block.find("timing ()", timing_pos)
                if timing_start < 0:
                    break
                timing_block = self._extract_block(pin_block, timing_start)
                timing_pos = timing_start + len(timing_block)
                related_match = re.search(r'related_pin\s*:\s*"([^"]+)"\s*;', timing_block)
                if related_match is None:
                    continue
                related_pin = related_match.group(1).strip()
                delay = self._parse_table_pair(timing_block, "cell_rise", "cell_fall")
                transition = self._parse_table_pair(
                    timing_block,
                    "rise_transition",
                    "fall_transition",
                )
                if delay is None or transition is None:
                    continue
                arcs[(pin_name, related_pin)] = ArcModel(delay=delay, transition=transition)
        return CellModel(input_caps=input_caps, arcs=arcs)

    def _parse_table_pair(self, block: str, lhs: str, rhs: str) -> TableModel | None:
        left = self._parse_table(block, lhs)
        right = self._parse_table(block, rhs)
        if left is None and right is None:
            return None
        if left is None:
            return right
        if right is None:
            return left
        rows: list[tuple[float, ...]] = []
        for left_row, right_row in zip(left.values, right.values):
            rows.append(tuple(max(a, b) for a, b in zip(left_row, right_row)))
        return TableModel(index_1=left.index_1, index_2=left.index_2, values=tuple(rows))

    def _parse_table(self, block: str, table_name: str) -> TableModel | None:
        start = block.find(f"{table_name} (")
        if start < 0:
            return None
        table_block = self._extract_block(block, start)
        index_1_match = re.search(r'index_1\s*\("([^"]+)"\)\s*;', table_block)
        index_2_match = re.search(r'index_2\s*\("([^"]+)"\)\s*;', table_block)
        values_match = re.search(r"values\s*\((.*?)\)\s*;", table_block, re.S)
        if index_1_match is None or index_2_match is None or values_match is None:
            return None
        index_1 = tuple(float(item.strip()) for item in index_1_match.group(1).split(","))
        index_2 = tuple(float(item.strip()) for item in index_2_match.group(1).split(","))
        row_matches = re.findall(r'"([^"]+)"', values_match.group(1))
        rows = tuple(
            tuple(float(item.strip()) for item in row.split(","))
            for row in row_matches
        )
        return TableModel(index_1=index_1, index_2=index_2, values=rows)

    def _extract_block(self, text: str, start: int) -> str:
        brace = text.find("{", start)
        depth = 0
        for idx in range(brace, len(text)):
            char = text[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]
        raise ValueError("unbalanced liberty block")


class NetlistBuilder:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.counter = 0
        self.inst_counter = 0
        self.zero = "const0"
        self.timing_model = LibertyTimingModel(LIBERTY_PATHS, MODELED_CELLS)
        self.signal_timing: dict[str, TimingState] = {
            self.zero: TimingState(arrival=0.0, slew=DEFAULT_INPUT_SLEW)
        }
        self.compressor_tree_ir = CompressorTreeIR(stages=(), outputs=())
        self.hot_suffix_lo = WIDTH
        self.phase_cache: dict[tuple[str, bool], PhaseOptions] = {}

    def new_wire(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}_{self.counter}"

    def emit(self, line: str = "") -> None:
        self.lines.append(line)

    def emit_pos_inst(self, cell: str, out: str, *ins: str) -> None:
        self.inst_counter += 1
        args = ", ".join((out, *ins))
        self.emit(f"{cell} g_{self.inst_counter}({args});")

    def pin_state(self, sig: str) -> TimingState:
        return self.signal_timing.get(sig, TimingState(arrival=0.0, slew=DEFAULT_INPUT_SLEW))

    def assign_timing(self, sig: str, state: TimingState) -> None:
        self.signal_timing[sig] = state

    def logic_and(self, a: str, b: str) -> str:
        if a == self.zero or b == self.zero:
            return self.zero
        out = self.new_wire("and")
        self.emit(f"wire {out};")
        self.emit_pos_inst(AND2_CELL, out, a, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                AND2_CELL,
                "Y",
                {"A": self.pin_state(a), "B": self.pin_state(b)},
            ),
        )
        return out

    def logic_nor(self, a: str, b: str) -> str:
        if a == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            return self.logic_inv(a)
        out = self.new_wire("nor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(NOR2_CELL, out, a, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                NOR2_CELL,
                "Y",
                {"A": self.pin_state(a), "B": self.pin_state(b)},
            ),
        )
        return out

    def logic_inv(self, a: str) -> str:
        if a == self.zero:
            return self.zero
        out = self.new_wire("inv")
        self.emit(f"wire {out};")
        self.emit_pos_inst("INVxp33_ASAP7_75t_R", out, a)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                "INVxp33_ASAP7_75t_R",
                "Y",
                {"A": self.pin_state(a)},
            ),
        )
        return out

    def logic_xor2(self, a: str, b: str, cell: str = XOR2_CELL) -> str:
        if a == self.zero:
            return b
        if b == self.zero:
            return a
        out = self.new_wire("xor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                cell,
                "Y",
                {"A": self.pin_state(a), "B": self.pin_state(b)},
            ),
        )
        return out

    def logic_xnor2(self, a: str, b: str, cell: str = XNOR2_CELL) -> str:
        if a == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            return self.logic_inv(a)
        out = self.new_wire("xnor")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                cell,
                "Y",
                {"A": self.pin_state(a), "B": self.pin_state(b)},
            ),
        )
        return out

    def phase_key(self, bit: PhasedBitRef) -> tuple[str, bool]:
        sig, _, inverted = bit
        return (sig, inverted)

    def register_phase_options(self, base: PhasedBitRef, options: PhaseOptions) -> None:
        self.phase_cache[self.phase_key(base)] = options
        self.phase_cache[self.phase_key(options.positive.bit)] = options
        self.phase_cache[self.phase_key(options.negative.bit)] = options

    def choose_best_bit(self, options: PhaseOptions) -> PhasedBitRef:
        pos = options.positive
        neg = options.negative
        pos_arrival = pos.bit[1]
        neg_arrival = neg.bit[1]
        if (pos_arrival, pos.inv_cost) <= (neg_arrival, neg.inv_cost):
            return pos.bit
        return neg.bit

    def option_cost(self, option: PhaseOption) -> tuple[float, int]:
        return (option.bit[1], option.inv_cost)

    def ensure_phase_option(self, bit: PhasedBitRef, want_inverted: bool) -> PhaseOption:
        sig, rank, inverted = bit
        if sig == self.zero or inverted == want_inverted:
            return PhaseOption((sig, rank, inverted), 0)
        inv_sig = self.logic_inv(sig)
        return PhaseOption((inv_sig, self.pin_state(inv_sig).arrival, want_inverted), 1)

    def phase_options(self, bit: PhasedBitRef) -> PhaseOptions:
        cached = self.phase_cache.get(self.phase_key(bit))
        if cached is not None:
            return cached
        positive = self.ensure_phase_option(bit, False)
        negative = self.ensure_phase_option(bit, True)
        options = PhaseOptions(positive=positive, negative=negative)
        self.register_phase_options(bit, options)
        return options

    def estimate_parity_plan(
        self,
        a: PhaseOption,
        b: PhaseOption,
        xor_cell: str,
        xnor_cell: str,
        want_inverted: bool,
    ) -> PhasePlan:
        a_sig, _, a_inv = a.bit
        b_sig, _, b_inv = b.bit
        if a_sig == self.zero:
            tail = self.ensure_phase_option(b.bit, want_inverted)
            return PhasePlan(
                arrival=tail.bit[1],
                inv_cost=a.inv_cost + b.inv_cost + tail.inv_cost,
                lhs=a,
                rhs=b,
                gate_kind="rhs_passthrough",
                want_inverted=want_inverted,
            )
        if b_sig == self.zero:
            tail = self.ensure_phase_option(a.bit, want_inverted)
            return PhasePlan(
                arrival=tail.bit[1],
                inv_cost=a.inv_cost + b.inv_cost + tail.inv_cost,
                lhs=a,
                rhs=b,
                gate_kind="lhs_passthrough",
                want_inverted=want_inverted,
            )

        pin_states = {"A": self.pin_state(a_sig), "B": self.pin_state(b_sig)}
        inv_parity = a_inv ^ b_inv
        candidates: list[PhasePlan] = []

        for kind, cell, out_phase in (
            ("xor", xor_cell, inv_parity),
            ("xnor", xnor_cell, not inv_parity),
        ):
            state = self.timing_model.propagate(cell, "Y", pin_states)
            total_inv = a.inv_cost + b.inv_cost
            final_arrival = state.arrival
            need_inv = out_phase != want_inverted
            if need_inv:
                state = self.timing_model.propagate("INVxp33_ASAP7_75t_R", "Y", {"A": state})
                total_inv += 1
                final_arrival = state.arrival
            candidates.append(
                PhasePlan(
                    arrival=final_arrival,
                    inv_cost=total_inv,
                    lhs=a,
                    rhs=b,
                    gate_kind=kind,
                    want_inverted=want_inverted,
                )
            )
        return min(candidates, key=lambda item: (item.arrival, item.inv_cost))

    def realize_parity_plan(
        self,
        plan: PhasePlan,
        xor_cell: str,
        xnor_cell: str,
    ) -> PhaseOption:
        a = plan.lhs
        b = plan.rhs
        kind = plan.gate_kind
        want_inverted = plan.want_inverted
        if kind == "rhs_passthrough":
            tail = self.ensure_phase_option(b.bit, want_inverted)
            return PhaseOption(tail.bit, plan.inv_cost)
        if kind == "lhs_passthrough":
            tail = self.ensure_phase_option(a.bit, want_inverted)
            return PhaseOption(tail.bit, plan.inv_cost)
        a_sig, _, a_inv = a.bit
        b_sig, _, b_inv = b.bit
        inv_parity = a_inv ^ b_inv
        if kind == "xor":
            out = self.logic_xor2(a_sig, b_sig, cell=xor_cell)
            out_phase = inv_parity
        else:
            out = self.logic_xnor2(a_sig, b_sig, cell=xnor_cell)
            out_phase = not inv_parity
        if out_phase != want_inverted:
            out = self.logic_inv(out)
        return PhaseOption((out, self.pin_state(out).arrival, want_inverted), plan.inv_cost)

    def phased_xor2(
        self,
        a: PhasedBitRef,
        b: PhasedBitRef,
        xor_cell: str = XOR2_CELL,
        xnor_cell: str = XNOR2_CELL,
        want_inverted: bool | None = None,
    ) -> PhasedBitRef:
        lhs = self.phase_options(a)
        rhs = self.phase_options(b)
        if want_inverted is None:
            options = self.combine_phase_options(lhs, rhs, xor_cell, xnor_cell)
            return self.choose_best_bit(options)
        return self.realize_parity_plan(
            self.estimate_parity_plan(
            lhs.negative if a[2] else lhs.positive,
            rhs.negative if b[2] else rhs.positive,
            xor_cell,
            xnor_cell,
            want_inverted,
            ),
            xor_cell,
            xnor_cell,
        ).bit

    def parity_views(
        self,
        a: PhasedBitRef,
        b: PhasedBitRef,
        xor_cell: str = XOR2_CELL,
        xnor_cell: str = XNOR2_CELL,
    ) -> tuple[PhasedBitRef, PhasedBitRef]:
        options = self.combine_phase_options(
            self.phase_options(a),
            self.phase_options(b),
            xor_cell,
            xnor_cell,
        )
        self.register_phase_options(options.positive.bit, options)
        return options.positive.bit, options.negative.bit

    def combine_phase_options(
        self,
        lhs: PhaseOptions,
        rhs: PhaseOptions,
        xor_cell: str,
        xnor_cell: str,
    ) -> PhaseOptions:
        def solve(want_inverted: bool) -> PhaseOption:
            candidates: list[PhasePlan] = []
            for a_opt in (lhs.positive, lhs.negative):
                for b_opt in (rhs.positive, rhs.negative):
                    candidates.append(
                        self.estimate_parity_plan(
                            a_opt,
                            b_opt,
                            xor_cell,
                            xnor_cell,
                            want_inverted,
                        )
                    )
            best = min(candidates, key=lambda item: (item.arrival, item.inv_cost))
            return self.realize_parity_plan(best, xor_cell, xnor_cell)

        return PhaseOptions(positive=solve(False), negative=solve(True))

    def logic_ao21(self, a1: str, a2: str, b: str, cell: str = AO21_CELL) -> str:
        if a1 == self.zero or a2 == self.zero:
            return b
        if b == self.zero:
            return self.logic_and(a1, a2)
        out = self.new_wire("ao21")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a1, a2, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                cell,
                "Y",
                {
                    "A1": self.pin_state(a1),
                    "A2": self.pin_state(a2),
                    "B": self.pin_state(b),
                },
            ),
        )
        return out

    def logic_aoi21(self, a1: str, a2: str, b: str, cell: str = AOI21_CELL) -> str:
        if a1 == self.zero or a2 == self.zero:
            return self.logic_inv(b)
        if b == self.zero:
            nand = self.new_wire("nand")
            self.emit(f"wire {nand};")
            self.emit_pos_inst("NAND2xp5_ASAP7_75t_R", nand, a1, a2)
            self.assign_timing(
                nand,
                self.timing_model.propagate(
                    "NAND2xp5_ASAP7_75t_R",
                    "Y",
                    {"A": self.pin_state(a1), "B": self.pin_state(a2)},
                ),
            )
            return nand
        out = self.new_wire("aoi21")
        self.emit(f"wire {out};")
        self.emit_pos_inst(cell, out, a1, a2, b)
        self.assign_timing(
            out,
            self.timing_model.propagate(
                cell,
                "Y",
                {
                    "A1": self.pin_state(a1),
                    "A2": self.pin_state(a2),
                    "B": self.pin_state(b),
                },
            ),
        )
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
        self.assign_timing(
            out,
            self.timing_model.propagate(
                MAJ_CELL,
                "Y",
                {"A": self.pin_state(a), "B": self.pin_state(b), "C": self.pin_state(c)},
            ),
        )
        return out

    def mixed_half_adder(self, a: str, b: str) -> tuple[str, str]:
        carry_bar = self.new_wire("ha_cbar")
        sum_bar = self.new_wire("ha_sbar")
        self.emit(f"wire {carry_bar};")
        self.emit(f"wire {sum_bar};")
        # HAxp5 emits complemented carry and complemented parity.
        self.emit_pos_inst("HAxp5_ASAP7_75t_R", carry_bar, sum_bar, a, b)
        input_states = {"A": self.pin_state(a), "B": self.pin_state(b)}
        self.assign_timing(
            carry_bar,
            self.timing_model.propagate("HAxp5_ASAP7_75t_R", "CON", input_states),
        )
        self.assign_timing(
            sum_bar,
            self.timing_model.propagate("HAxp5_ASAP7_75t_R", "SN", input_states),
        )
        return sum_bar, carry_bar

    def mixed_full_adder(self, a: str, b: str, c: str) -> tuple[str, str]:
        carry_bar = self.new_wire("fa_cbar")
        sum_bar = self.new_wire("fa_sbar")
        self.emit(f"wire {carry_bar};")
        self.emit(f"wire {sum_bar};")
        # FAx1 emits complemented carry and complemented parity.
        self.emit_pos_inst("FAx1_ASAP7_75t_R", carry_bar, sum_bar, a, b, c)
        input_states = {"A": self.pin_state(a), "B": self.pin_state(b), "CI": self.pin_state(c)}
        self.assign_timing(
            carry_bar,
            self.timing_model.propagate("FAx1_ASAP7_75t_R", "CON", input_states),
        )
        self.assign_timing(
            sum_bar,
            self.timing_model.propagate("FAx1_ASAP7_75t_R", "SN", input_states),
        )
        return sum_bar, carry_bar

    def materialize_positive(self, bit: PhasedBitRef) -> PhasedBitRef:
        return self.phase_options(bit).positive.bit

    def logic_xor3(self, a: str, b: str, c: str) -> str:
        return self.logic_xor2(
            self.logic_xor2(a, b, cell=COMPRESS_XOR2_CELL),
            c,
            cell=COMPRESS_XOR2_CELL,
        )

    def prefix_xor_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo:
            return XOR2_CELL
        if PREFIX_FAST_LO <= bit_idx <= PREFIX_FAST_HI:
            return XOR2_CELL
        return COMPRESS_XOR2_CELL

    def prefix_xnor_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo:
            return XNOR2_FAST_CELL
        if PREFIX_FAST_LO <= bit_idx <= PREFIX_FAST_HI:
            return XNOR2_FAST_CELL
        return XNOR2_CELL

    def prefix_ao21_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo:
            return AO21_FAST_CELL
        return AO21_CELL

    def final_carry_aoi21_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo - 1:
            return FINAL_CARRY_STRONG_AOI21_CELL
        return AOI21_CELL

    def output_xor_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo:
            return XOR2_CELL
        return OUTPUT_XOR2_CELL

    def output_xnor_cell(self, bit_idx: int) -> str:
        if bit_idx >= self.hot_suffix_lo:
            return XNOR2_FAST_CELL
        return XNOR2_CELL

    def compress_xor_cell(self, bit_idx: int) -> str:
        if COMPRESS_FAST_LO <= bit_idx <= COMPRESS_FAST_HI:
            return COMPRESS_FAST_XOR2_CELL
        return COMPRESS_XOR2_CELL

    def compress_xnor_cell(self, bit_idx: int) -> str:
        if COMPRESS_FAST_LO <= bit_idx <= COMPRESS_FAST_HI:
            return XNOR2_FAST_CELL
        return XNOR2_CELL

    def compress_first_xor_cell(self, bit_idx: int) -> str:
        if AGGRESSIVE_COMPRESS_LO <= bit_idx <= AGGRESSIVE_COMPRESS_HI:
            return COMPRESS_FAST_XOR2_CELL
        # Outside the timing-critical high-bit window keep the first XOR on
        # the smaller cell and spend the faster variants only on the second
        # sum combine.
        return COMPRESS_XOR2_CELL

    def compress_first_xnor_cell(self, bit_idx: int) -> str:
        if AGGRESSIVE_COMPRESS_LO <= bit_idx <= AGGRESSIVE_COMPRESS_HI:
            return XNOR2_FAST_CELL
        return XNOR2_CELL

    def prefer_late_compress(self, target: int, bit_idx: int) -> bool:
        return False

    def use_mixed_compressor(self, target: int, bit_idx: int) -> bool:
        if not MIXED_HIGH_LO <= bit_idx <= MIXED_HIGH_HI:
            return False
        return target == 2

    def pick_operands(
        self,
        work: list[PhasedBitRef],
        count: int,
        prefer_late: bool,
    ) -> list[PhasedBitRef]:
        picked: list[PhasedBitRef] = []
        for _ in range(count):
            picked.append(work.pop(-1) if prefer_late else work.pop(0))
        picked.sort(key=lambda item: item[1])
        return picked

    def half_adder(
        self, a: PhasedBitRef, b: PhasedBitRef, bit_idx: int
    ) -> tuple[PhasedBitRef, PhasedBitRef]:
        sum_options = self.combine_phase_options(
            self.phase_options(a),
            self.phase_options(b),
            self.compress_xor_cell(bit_idx),
            self.compress_xnor_cell(bit_idx),
        )
        sum_bit = self.choose_best_bit(sum_options)
        self.register_phase_options(sum_bit, sum_options)
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        if a_sig == self.zero:
            return (b_sig, b_rank, False), (self.zero, -1, False)
        if b_sig == self.zero:
            return (a_sig, a_rank, False), (self.zero, -1, False)
        carry_wire = self.logic_and(a_sig, b_sig)
        return (
            sum_bit,
            (carry_wire, self.pin_state(carry_wire).arrival, False),
        )

    def full_adder(
        self, a: PhasedBitRef, b: PhasedBitRef, c: PhasedBitRef, bit_idx: int
    ) -> tuple[PhasedBitRef, PhasedBitRef]:
        xor_ab_options = self.combine_phase_options(
            self.phase_options(a),
            self.phase_options(b),
            self.compress_first_xor_cell(bit_idx),
            self.compress_first_xnor_cell(bit_idx),
        )
        xor_ab = self.choose_best_bit(xor_ab_options)
        self.register_phase_options(xor_ab, xor_ab_options)
        sum_options = self.combine_phase_options(
            xor_ab_options,
            self.phase_options(c),
            self.compress_xor_cell(bit_idx),
            self.compress_xnor_cell(bit_idx),
        )
        sum_bit = self.choose_best_bit(sum_options)
        self.register_phase_options(sum_bit, sum_options)
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        c_sig, c_rank, _ = self.materialize_positive(c)
        if a_sig == self.zero:
            return self.half_adder(b, c, bit_idx)
        if b_sig == self.zero:
            return self.half_adder(a, c, bit_idx)
        if c_sig == self.zero:
            return self.half_adder(a, b, bit_idx)
        carry_wire = self.logic_maj3(a_sig, b_sig, c_sig)
        return (
            sum_bit,
            (carry_wire, self.pin_state(carry_wire).arrival, False),
        )

    def mixed_stage_half_adder(self, a: PhasedBitRef, b: PhasedBitRef) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        sum_bar, carry_bar = self.mixed_half_adder(a_sig, b_sig)
        return (
            (sum_bar, self.pin_state(sum_bar).arrival, True),
            (carry_bar, self.pin_state(carry_bar).arrival, True),
        )

    def mixed_stage_full_adder(self, a: PhasedBitRef, b: PhasedBitRef, c: PhasedBitRef) -> tuple[PhasedBitRef, PhasedBitRef]:
        a_sig, a_rank, _ = self.materialize_positive(a)
        b_sig, b_rank, _ = self.materialize_positive(b)
        c_sig, c_rank, _ = self.materialize_positive(c)
        sum_bar, carry_bar = self.mixed_full_adder(a_sig, b_sig, c_sig)
        return (
            (sum_bar, self.pin_state(sum_bar).arrival, True),
            (carry_bar, self.pin_state(carry_bar).arrival, True),
        )

    def reduce_dadda(self, cols: list[list[PhasedBitRef]]) -> list[list[PhasedBitRef]]:
        max_height = max(len(col) for col in cols[:-1])
        limits = [2]
        while limits[-1] < max_height:
            limits.append((limits[-1] * 3) // 2)

        stages: list[CompressorStage] = []
        for target in reversed(limits[:-1]):
            stage_cols = [sorted(list(col), key=lambda item: item[1]) for col in cols]
            next_cols: list[list[PhasedBitRef]] = [[] for _ in cols]
            ops: list[CompressorOp] = []
            for idx in range(len(cols) - 1):
                # Compress earlier-arriving bits first so late signals avoid
                # extra sum-stage depth when the column is over target height.
                # Carries generated in this stage are deferred to the next stage
                # so the tree does not collapse into an intra-stage MAJ chain.
                work = list(stage_cols[idx])
                carried_in = len(next_cols[idx])
                reduced: list[PhasedBitRef] = []
                while carried_in + len(reduced) + len(work) > target:
                    excess = carried_in + len(reduced) + len(work) - target
                    use_mixed = self.use_mixed_compressor(target, idx)
                    prefer_late = self.prefer_late_compress(target, idx)
                    if excess == 1:
                        a, b = self.pick_operands(work, 2, prefer_late)
                        if use_mixed:
                            sum_wire, carry_wire = self.mixed_stage_half_adder(a, b)
                        else:
                            sum_wire, carry_wire = self.half_adder(a, b, idx)
                        op_kind = "ha"
                        input_bits = (a, b)
                    else:
                        a, b, c = self.pick_operands(work, 3, prefer_late)
                        if use_mixed:
                            sum_wire, carry_wire = self.mixed_stage_full_adder(a, b, c)
                        else:
                            sum_wire, carry_wire = self.full_adder(a, b, c, idx)
                        op_kind = "fa"
                        input_bits = (a, b, c)
                    ops.append(
                        CompressorOp(
                            kind=op_kind,
                            column=idx,
                            use_mixed=use_mixed,
                            inputs=tuple(bit[0] for bit in input_bits),
                            sum_out=sum_wire[0],
                            carry_out=carry_wire[0],
                        )
                    )
                    reduced.append(sum_wire)
                    next_cols[idx + 1].append(carry_wire)
                reduced.extend(work)
                next_cols[idx].extend(sorted(reduced, key=lambda item: item[1]))
            next_cols[-1].extend(stage_cols[-1])
            cols = [sorted(col, key=lambda item: item[1]) for col in next_cols]
            stages.append(CompressorStage(target=target, operations=tuple(ops)))
        self.compressor_tree_ir = CompressorTreeIR(
            stages=tuple(stages),
            outputs=tuple(tuple(bit[0] for bit in col) for col in cols),
        )
        return cols

    def select_hot_suffix(self, cols: list[list[PhasedBitRef]]) -> int:
        op_counts = [0] * WIDTH
        mixed_counts = [0] * WIDTH
        for stage in self.compressor_tree_ir.stages:
            for op in stage.operations:
                if 0 <= op.column < WIDTH:
                    op_counts[op.column] += 1
                    if op.use_mixed:
                        mixed_counts[op.column] += 1

        candidates: list[tuple[float, int]] = []
        for idx in range(HOT_SUFFIX_CANDIDATE_LO, WIDTH - 1):
            arrival = max((bit[1] for bit in cols[idx]), default=0.0)
            score = arrival + 8.0 * op_counts[idx] + 12.0 * mixed_counts[idx]
            if len(self.compressor_tree_ir.outputs[idx]) >= 2:
                score += 6.0
            candidates.append((score, idx))
        if not candidates:
            return WIDTH

        top_cols = sorted(candidates, reverse=True)[:HOT_SUFFIX_TOP_K]
        return max(HOT_SUFFIX_CANDIDATE_LO, min(idx for _, idx in top_cols) - 1)

    def rewrite_hot_suffix_rows(self, cols: list[list[PhasedBitRef]]) -> list[list[PhasedBitRef]]:
        rewritten: list[list[PhasedBitRef]] = []
        for idx, col in enumerate(cols):
            ordered = list(col)
            if self.hot_suffix_lo <= idx <= AGGRESSIVE_COMPRESS_HI and len(ordered) >= 2:
                ordered.sort(key=lambda item: item[1])
            rewritten.append(ordered)
        self.compressor_tree_ir = CompressorTreeIR(
            stages=self.compressor_tree_ir.stages,
            outputs=tuple(tuple(col) for col in rewritten),
        )
        return rewritten

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
        for idx in range(16):
            self.assign_timing(f"A[{idx}]", TimingState(arrival=0.0, slew=DEFAULT_INPUT_SLEW))
            self.assign_timing(f"B[{idx}]", TimingState(arrival=0.0, slew=DEFAULT_INPUT_SLEW))
        for idx in range(WIDTH):
            self.assign_timing(f"C[{idx}]", TimingState(arrival=0.0, slew=DEFAULT_INPUT_SLEW))

        for i in range(16):
            for j in range(16):
                pp = self.new_wire("pp")
                self.emit(f"wire {pp};")
                self.emit_pos_inst(AND2_CELL, pp, f"A[{i}]", f"B[{j}]")
                self.assign_timing(
                    pp,
                    self.timing_model.propagate(
                        AND2_CELL,
                        "Y",
                        {"A": self.pin_state(f"A[{i}]"), "B": self.pin_state(f"B[{j}]")},
                    ),
                )
                cols[i + j].append((pp, self.pin_state(pp).arrival, False))

        for bit in range(WIDTH):
            cols[bit].append((f"C[{bit}]", self.pin_state(f"C[{bit}]").arrival, False))

        cols = self.reduce_dadda(cols)
        self.hot_suffix_lo = self.select_hot_suffix(cols)
        cols = self.rewrite_hot_suffix_rows(cols)

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

        bit_p_phase: list[PhasedBitRef] = []
        p_prev: list[str] = []
        g_prev: list[str] = []
        top_sum_phase: PhasedBitRef = (self.zero, -1, False)
        for idx in range(WIDTH - 1):
            a_bit = row_a_bits[idx]
            b_bit = row_b_bits[idx]
            a_sig, _, a_inv = a_bit
            b_sig, _, b_inv = b_bit
            p_pos, p_phase = self.parity_views(
                a_bit,
                b_bit,
                xor_cell=self.prefix_xor_cell(idx),
                xnor_cell=self.prefix_xnor_cell(idx),
            )
            if a_sig == self.zero or b_sig == self.zero:
                a_pos, _, _ = self.materialize_positive(a_bit)
                b_pos, _, _ = self.materialize_positive(b_bit)
                g = self.logic_and(a_pos, b_pos)
            elif a_inv == b_inv:
                if a_inv:
                    g = self.logic_nor(a_sig, b_sig)
                else:
                    g = self.logic_and(a_sig, b_sig)
            else:
                a_pos, _, _ = self.materialize_positive(a_bit)
                b_pos, _, _ = self.materialize_positive(b_bit)
                g = self.logic_and(a_pos, b_pos)
            bit_p_phase.append(p_phase)
            p_prev.append(p_pos[0])
            g_prev.append(g)

        a_bit = row_a_bits[WIDTH - 1]
        b_bit = row_b_bits[WIDTH - 1]
        _, top_sum_phase = self.parity_views(
            a_bit,
            b_bit,
            xor_cell=self.output_xor_cell(WIDTH - 1),
            xnor_cell=self.output_xnor_cell(WIDTH - 1),
        )

        for distance in (1, 2, 4, 8):
            p_next: list[str] = []
            g_next: list[str] = []
            for idx in range(WIDTH - 1):
                if idx < distance:
                    p = p_prev[idx]
                    g = g_prev[idx]
                else:
                    p = self.logic_and(p_prev[idx], p_prev[idx - distance])
                    g = self.logic_ao21(
                        p_prev[idx],
                        g_prev[idx - distance],
                        g_prev[idx],
                        cell=self.prefix_ao21_cell(idx),
                    )
                p_next.append(p)
                g_next.append(g)
            p_prev = p_next
            g_prev = g_next

        final_carry_bar = [self.zero] * WIDTH
        for idx in range(16, WIDTH - 1):
            cell = self.final_carry_aoi21_cell(idx)
            final_carry_bar[idx] = self.logic_aoi21(
                p_prev[idx],
                g_prev[idx - 16],
                g_prev[idx],
                cell=cell,
            )

        self.emit("")
        for idx in range(WIDTH - 1):
            if idx == 0:
                sum_bit = bit_p_phase[idx]
            elif idx <= 16:
                sum_bit = self.phased_xor2(
                    (g_prev[idx - 1], self.pin_state(g_prev[idx - 1]).arrival, False),
                    bit_p_phase[idx],
                    xor_cell=self.output_xor_cell(idx),
                    xnor_cell=self.output_xnor_cell(idx),
                )
            else:
                sum_bit = self.phased_xor2(
                    (final_carry_bar[idx - 1], self.pin_state(final_carry_bar[idx - 1]).arrival, True),
                    bit_p_phase[idx],
                    xor_cell=self.output_xor_cell(idx),
                    xnor_cell=self.output_xnor_cell(idx),
                )
            sum_wire, _, _ = self.materialize_positive(sum_bit)
            self.emit(f"assign D[{idx}] = {sum_wire};")
        sum_bit = self.phased_xor2(
            (final_carry_bar[WIDTH - 2], self.pin_state(final_carry_bar[WIDTH - 2]).arrival, True),
            top_sum_phase,
            xor_cell=self.output_xor_cell(WIDTH - 1),
            xnor_cell=self.output_xnor_cell(WIDTH - 1),
        )
        sum_wire, _, _ = self.materialize_positive(sum_bit)
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
