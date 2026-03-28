"""Liberty-backed NLDM timing and pin-capacitance lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import re


_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_CAP_RE = re.compile(r"\bcapacitance\s*:\s*([-+0-9.eE]+)\s*;")
_INDEX_RE = re.compile(r"index_(?P<axis>[12])\s*\(\s*\"([^\"]+)\"\s*\)\s*;")
_VALUES_RE = re.compile(r"values\s*\((.*?)\)\s*;", re.S)
_RELATED_PIN_RE = re.compile(r"\brelated_pin\s*:\s*\"([^\"]+)\"\s*;")


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text)


def _find_matching_brace(text: str, open_brace: int) -> int:
    depth = 0
    for idx in range(open_brace, len(text)):
        if text[idx] == "{":
            depth += 1
            continue
        if text[idx] != "}":
            continue
        depth -= 1
        if depth == 0:
            return idx
    raise AssertionError("Unbalanced liberty braces")


def _iter_blocks(text: str, keyword: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"\b{re.escape(keyword)}\s*\(([^)]*)\)\s*\{{", re.M)
    blocks: list[tuple[str, str]] = []
    for match in pattern.finditer(text):
        open_brace = text.find("{", match.start())
        close_brace = _find_matching_brace(text, open_brace)
        blocks.append((match.group(1).strip().strip('"'), text[open_brace + 1 : close_brace]))
    return blocks


def _parse_number_list(raw: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in raw.split(",") if item.strip())


def _parse_table(block: str) -> tuple[tuple[float, ...], tuple[float, ...], tuple[tuple[float, ...], ...]] | None:
    indices: dict[str, tuple[float, ...]] = {}
    for match in _INDEX_RE.finditer(block):
        indices[match.group("axis")] = _parse_number_list(match.group(2))

    values_match = _VALUES_RE.search(block)
    if values_match is None or "1" not in indices:
        return None

    rows = re.findall(r"\"([^\"]+)\"", values_match.group(1))
    matrix = tuple(_parse_number_list(row) for row in rows)
    index_2 = indices.get("2", ())
    return indices["1"], index_2, matrix


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _interp_axis(value: float, axis: tuple[float, ...]) -> tuple[int, int, float]:
    if len(axis) == 1:
        return 0, 0, 0.0
    clamped = _clamp(value, axis[0], axis[-1])
    for idx in range(len(axis) - 1):
        lo = axis[idx]
        hi = axis[idx + 1]
        if lo <= clamped <= hi:
            if hi == lo:
                return idx, idx + 1, 0.0
            return idx, idx + 1, (clamped - lo) / (hi - lo)
    return len(axis) - 2, len(axis) - 1, 1.0


def _lookup_table(
    *,
    index_1: tuple[float, ...],
    index_2: tuple[float, ...],
    values: tuple[tuple[float, ...], ...],
    x: float,
    y: float,
) -> float:
    i0, i1, tx = _interp_axis(x, index_1)
    if not index_2:
        v0 = values[i0][0]
        v1 = values[i1][0]
        return v0 + (v1 - v0) * tx

    j0, j1, ty = _interp_axis(y, index_2)
    q00 = values[i0][j0]
    q01 = values[i0][j1]
    q10 = values[i1][j0]
    q11 = values[i1][j1]
    v0 = q00 + (q01 - q00) * ty
    v1 = q10 + (q11 - q10) * ty
    return v0 + (v1 - v0) * tx


@dataclass(frozen=True)
class LookupTable:
    index_1: tuple[float, ...]
    index_2: tuple[float, ...]
    values: tuple[tuple[float, ...], ...]

    def lookup(self, x: float, y: float) -> float:
        return _lookup_table(
            index_1=self.index_1,
            index_2=self.index_2,
            values=self.values,
            x=x,
            y=y,
        )


@dataclass(frozen=True)
class LibertyArc:
    related_pin: str
    cell_rise: LookupTable | None = None
    cell_fall: LookupTable | None = None
    rise_transition: LookupTable | None = None
    fall_transition: LookupTable | None = None

    def delay_ps(self, input_slew_ps: float, load_ff: float) -> float:
        choices = [
            table.lookup(input_slew_ps, load_ff)
            for table in (self.cell_rise, self.cell_fall)
            if table is not None
        ]
        if not choices:
            raise AssertionError(f"Missing delay table for liberty arc driven by {self.related_pin!r}")
        return max(choices)

    def transition_ps(self, input_slew_ps: float, load_ff: float) -> float:
        choices = [
            table.lookup(input_slew_ps, load_ff)
            for table in (self.rise_transition, self.fall_transition)
            if table is not None
        ]
        if not choices:
            raise AssertionError(f"Missing transition table for liberty arc driven by {self.related_pin!r}")
        return max(choices)


@dataclass(frozen=True)
class CellModel:
    input_caps_ff: dict[str, float] = field(default_factory=dict)
    output_arcs: dict[tuple[str, str], tuple[LibertyArc, ...]] = field(default_factory=dict)


@dataclass
class LibertyModel:
    search_paths: list[str] = field(default_factory=list)
    cells: dict[str, CellModel] = field(default_factory=dict)

    def pin_capacitance(self, cell: str, pin: str) -> float:
        cell_model = self.cells.get(cell)
        if cell_model is None:
            raise AssertionError(f"Unknown liberty cell {cell!r}")
        return cell_model.input_caps_ff.get(pin, 0.0)

    def delay(self, cell: str, arc: tuple[str, str], input_slew: float, load: float) -> float:
        """Return the worst-case arc delay in ns for the given slew/load point."""

        cell_model = self.cells.get(cell)
        if cell_model is None:
            raise AssertionError(f"Unknown liberty cell {cell!r}")
        arcs = cell_model.output_arcs.get(arc)
        if not arcs:
            raise AssertionError(f"Missing liberty arc {arc!r} for cell {cell!r}")
        input_slew_ps = max(input_slew, 0.0) * 1000.0
        load_ff = max(load, 0.0)
        return max(entry.delay_ps(input_slew_ps, load_ff) for entry in arcs) / 1000.0

    def transition(self, cell: str, arc: tuple[str, str], input_slew: float, load: float) -> float:
        """Return the worst-case output slew in ns for the given arc."""

        cell_model = self.cells.get(cell)
        if cell_model is None:
            raise AssertionError(f"Unknown liberty cell {cell!r}")
        arcs = cell_model.output_arcs.get(arc)
        if not arcs:
            raise AssertionError(f"Missing liberty arc {arc!r} for cell {cell!r}")
        input_slew_ps = max(input_slew, 0.0) * 1000.0
        load_ff = max(load, 0.0)
        return max(entry.transition_ps(input_slew_ps, load_ff) for entry in arcs) / 1000.0

    @classmethod
    def from_files(cls, paths: list[Path]) -> "LibertyModel":
        model = cls(search_paths=[str(path) for path in paths])
        for path in paths:
            model._load_file(path)
        return model

    def _load_file(self, path: Path) -> None:
        text = _strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        for cell_name, cell_body in _iter_blocks(text, "cell"):
            self.cells[cell_name] = _parse_cell(cell_body)


def _parse_cell(body: str) -> CellModel:
    input_caps: dict[str, float] = {}
    arcs: dict[tuple[str, str], list[LibertyArc]] = {}

    for pin_name, pin_body in _iter_blocks(body, "pin"):
        direction_match = re.search(r"\bdirection\s*:\s*(input|output)\s*;", pin_body)
        if direction_match is None:
            continue
        direction = direction_match.group(1)
        if direction == "input":
            cap_match = _CAP_RE.search(pin_body)
            if cap_match is not None:
                input_caps[pin_name] = float(cap_match.group(1))
            continue

        for _, timing_body in _iter_blocks(pin_body, "timing"):
            related_pin_match = _RELATED_PIN_RE.search(timing_body)
            if related_pin_match is None:
                continue
            related_pin = related_pin_match.group(1)
            cell_rise = _read_lookup_table(timing_body, "cell_rise")
            cell_fall = _read_lookup_table(timing_body, "cell_fall")
            rise_transition = _read_lookup_table(timing_body, "rise_transition")
            fall_transition = _read_lookup_table(timing_body, "fall_transition")
            arc = LibertyArc(
                related_pin=related_pin,
                cell_rise=cell_rise,
                cell_fall=cell_fall,
                rise_transition=rise_transition,
                fall_transition=fall_transition,
            )
            arcs.setdefault((related_pin, pin_name), []).append(arc)

    return CellModel(
        input_caps_ff=input_caps,
        output_arcs={key: tuple(value) for key, value in arcs.items()},
    )


def _read_lookup_table(block: str, keyword: str) -> LookupTable | None:
    matches = _iter_blocks(block, keyword)
    if not matches:
        return None
    parsed = _parse_table(matches[0][1])
    if parsed is None:
        return None
    index_1, index_2, values = parsed
    return LookupTable(index_1=index_1, index_2=index_2, values=values)


def _default_liberty_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[3]
    return [
        repo_root / "tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib",
        repo_root / "tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib",
        repo_root / "tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib",
        repo_root / "tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib",
        repo_root / "tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
    ]


@lru_cache(maxsize=1)
def load_default_liberty_model() -> LibertyModel:
    return LibertyModel.from_files(_default_liberty_paths())
