from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin
from pathlib import Path


ALLOWED_ENTITIES = {"LINE", "ARC", "CIRCLE", "POLYLINE", "VERTEX", "SEQEND", "SECTION", "ENDSEC", "EOF"}
FORBIDDEN_ENTITIES = {"SPLINE", "HATCH", "TEXT", "MTEXT", "DIMENSION", "INSERT", "BLOCK", "ELLIPSE", "3DFACE", "SOLID"}


@dataclass
class DxfValidationResult:
    path: str
    entity_count: int = 0
    forbidden_entities: list[str] = field(default_factory=list)
    unknown_entities: list[str] = field(default_factory=list)
    bbox: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.forbidden_entities and not self.unknown_entities


Record = tuple[str, list[tuple[str, str]]]


def validate_dxf(path: str | Path) -> DxfValidationResult:
    """Valida o DXF contra o contrato de corte.

    Somente a secao ENTITIES e inspecionada para entidades de corte. Tabelas e o
    BLOCKS padrao do R12 ($MODEL_SPACE/$PAPER_SPACE) sao aceitos; blocos de
    usuario, ou entidades dentro de BLOCKS, sao rejeitados.
    """
    target = Path(path)
    raw = target.read_text(encoding="latin-1").splitlines()
    sections = _sections(_pairs(raw))
    entities = _records(sections.get("ENTITIES", []))

    forbidden: set[str] = set()
    unknown: set[str] = set()
    for kind, _ in entities:
        _classify(kind, forbidden, unknown)

    for kind, data in _records(sections.get("BLOCKS", [])):
        if kind == "BLOCK":
            name = next((value for code, value in data if code == "2"), "")
            if not _is_default_space_block(name):
                forbidden.add("BLOCK")
        elif kind != "ENDBLK":
            _classify(kind, forbidden, unknown)

    result = DxfValidationResult(path=str(target), entity_count=len(entities))
    result.forbidden_entities = sorted(forbidden)
    result.unknown_entities = sorted(unknown)
    result.bbox = _bbox(entities)
    return result


def _is_default_space_block(name: str) -> bool:
    # R12 usa $MODEL_SPACE/$PAPER_SPACE; versoes posteriores usam *Model_Space/*Paper_Space.
    return name.upper() in {"$MODEL_SPACE", "$PAPER_SPACE", "*MODEL_SPACE", "*PAPER_SPACE"}


def _classify(kind: str, forbidden: set[str], unknown: set[str]) -> None:
    if kind in FORBIDDEN_ENTITIES:
        forbidden.add(kind)
    elif kind not in ALLOWED_ENTITIES:
        unknown.add(kind)


def _pairs(lines: list[str]) -> list[tuple[str, str]]:
    return [(lines[index].strip(), lines[index + 1].strip()) for index in range(0, len(lines) - 1, 2)]


def _sections(pairs: list[tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
    sections: dict[str, list[tuple[str, str]]] = {}
    index = 0
    while index < len(pairs):
        code, value = pairs[index]
        if code == "0" and value.upper() == "SECTION" and index + 1 < len(pairs) and pairs[index + 1][0] == "2":
            name = pairs[index + 1][1].upper()
            index += 2
            body: list[tuple[str, str]] = []
            while index < len(pairs) and not (pairs[index][0] == "0" and pairs[index][1].upper() == "ENDSEC"):
                body.append(pairs[index])
                index += 1
            sections[name] = body
        index += 1
    return sections


def _records(body: list[tuple[str, str]]) -> list[Record]:
    records: list[Record] = []
    for code, value in body:
        if code == "0":
            records.append((value.upper(), []))
        elif records:
            records[-1][1].append((code, value))
    return records


def _num(data: list[tuple[str, str]], code: str) -> float | None:
    for key, value in data:
        if key == code:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _bbox(entities: list[Record]) -> dict[str, float]:
    points: list[tuple[float, float]] = []
    for kind, data in entities:
        if kind == "LINE":
            for xc, yc in (("10", "20"), ("11", "21")):
                x, y = _num(data, xc), _num(data, yc)
                if x is not None and y is not None:
                    points.append((x, y))
        elif kind == "VERTEX":
            x, y = _num(data, "10"), _num(data, "20")
            if x is not None and y is not None:
                points.append((x, y))
        elif kind == "CIRCLE":
            cx, cy, r = _num(data, "10"), _num(data, "20"), _num(data, "40")
            if None not in (cx, cy, r):
                points.extend([(cx - r, cy - r), (cx + r, cy + r)])
        elif kind == "ARC":
            cx, cy, r = _num(data, "10"), _num(data, "20"), _num(data, "40")
            a0, a1 = _num(data, "50"), _num(data, "51")
            if None not in (cx, cy, r, a0, a1):
                points.extend(_arc_points(cx, cy, r, a0, a1))
    if not points:
        return {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0, "width": 0, "height": 0}
    min_x = min(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_x = max(x for x, _ in points)
    max_y = max(y for _, y in points)
    return {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y, "width": max_x - min_x, "height": max_y - min_y}


def _arc_points(cx: float, cy: float, r: float, a0: float, a1: float) -> list[tuple[float, float]]:
    start, end = a0 % 360.0, a1 % 360.0
    sweep = (end - start) % 360.0 or 360.0
    points = [(cx + r * cos(radians(a)), cy + r * sin(radians(a))) for a in (start, end)]
    for cardinal in (0.0, 90.0, 180.0, 270.0):
        if (cardinal - start) % 360.0 <= sweep:
            points.append((cx + r * cos(radians(cardinal)), cy + r * sin(radians(cardinal))))
    return points
