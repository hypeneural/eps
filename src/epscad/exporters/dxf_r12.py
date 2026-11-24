from __future__ import annotations

from math import atan2, degrees, hypot
from pathlib import Path

from epscad.schema import CutJobResult, PathSegment


SUPPORTED_KINDS = {"LINE", "ARC", "CIRCLE"}


def write_dxf_r12(job: CutJobResult, path: str | Path, *, use_ezdxf: bool = True) -> Path:
    """Escreve o DXF R12 de corte.

    Usa ``ezdxf`` quando instalado; caso contrario usa um escritor textual que
    gera a estrutura R12 completa (HEADER, TABLES/LTYPE/LAYER, ENTITIES, EOF).
    Tipos de segmento nao suportados geram erro explicito (nunca sao descartados).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    segments = _segments(job)
    _check_supported(segments)
    if use_ezdxf:
        try:
            import ezdxf
        except Exception:
            ezdxf = None
        if ezdxf is not None:
            _write_with_ezdxf(ezdxf, segments, target)
            return target
    _write_text_dxf(segments, target)
    return target


def _check_supported(segments: list[PathSegment]) -> None:
    for segment in segments:
        kind = segment.kind.upper()
        if kind not in SUPPORTED_KINDS:
            raise ValueError(f"Unsupported segment kind for DXF R12 export: {segment.kind!r}")
        if kind in {"ARC", "CIRCLE"} and segment.center is None:
            raise ValueError(f"{kind} segment requires center")


def _write_with_ezdxf(ezdxf, segments: list[PathSegment], target: Path) -> None:
    doc = ezdxf.new("R12")
    modelspace = doc.modelspace()
    for layer in sorted({segment.layer for segment in segments}):
        if layer not in doc.layers:
            doc.layers.add(layer)
    for segment in segments:
        attribs = {"layer": segment.layer}
        kind = segment.kind.upper()
        if kind == "LINE":
            modelspace.add_line((segment.start.x, segment.start.y, 0), (segment.end.x, segment.end.y, 0), dxfattribs=attribs)
        elif kind == "CIRCLE":
            center, radius, _, _ = _arc_params(segment)
            modelspace.add_circle((center.x, center.y, 0), radius, dxfattribs=attribs)
        else:
            center, radius, start_angle, end_angle = _arc_params(segment)
            modelspace.add_arc((center.x, center.y, 0), radius, start_angle, end_angle, dxfattribs=attribs)
    doc.saveas(target)


def _arc_params(segment: PathSegment):
    center = segment.center
    radius = hypot(segment.start.x - center.x, segment.start.y - center.y)
    start_angle = degrees(atan2(segment.start.y - center.y, segment.start.x - center.x))
    end_angle = degrees(atan2(segment.end.y - center.y, segment.end.x - center.x))
    if not segment.ccw:
        start_angle, end_angle = end_angle, start_angle
    return center, radius, start_angle % 360.0, end_angle % 360.0


def _write_text_dxf(segments: list[PathSegment], target: Path) -> None:
    layers = sorted({segment.layer for segment in segments}) or ["0"]
    lines: list[str] = []
    add = lines.extend
    add(["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC"])
    add(["0", "SECTION", "2", "TABLES"])
    add(["0", "TABLE", "2", "LTYPE", "70", "1"])
    add(["0", "LTYPE", "2", "CONTINUOUS", "70", "0", "3", "Solid line", "72", "65", "73", "0", "40", "0.0"])
    add(["0", "ENDTAB"])
    add(["0", "TABLE", "2", "LAYER", "70", str(len(layers))])
    for layer in layers:
        add(["0", "LAYER", "2", layer, "70", "0", "62", "7", "6", "CONTINUOUS"])
    add(["0", "ENDTAB"])
    add(["0", "ENDSEC"])
    add(["0", "SECTION", "2", "ENTITIES"])
    for segment in segments:
        kind = segment.kind.upper()
        if kind == "LINE":
            add(["0", "LINE", "8", segment.layer])
            add(["10", _fmt(segment.start.x), "20", _fmt(segment.start.y), "30", "0.0"])
            add(["11", _fmt(segment.end.x), "21", _fmt(segment.end.y), "31", "0.0"])
        elif kind == "CIRCLE":
            center, radius, _, _ = _arc_params(segment)
            add(["0", "CIRCLE", "8", segment.layer, "10", _fmt(center.x), "20", _fmt(center.y), "30", "0.0", "40", _fmt(radius)])
        else:
            center, radius, start_angle, end_angle = _arc_params(segment)
            add(["0", "ARC", "8", segment.layer, "10", _fmt(center.x), "20", _fmt(center.y), "30", "0.0", "40", _fmt(radius)])
            add(["50", _fmt(start_angle), "51", _fmt(end_angle)])
    add(["0", "ENDSEC", "0", "EOF", ""])
    target.write_text("\n".join(lines), encoding="ascii")


def _segments(job: CutJobResult) -> list[PathSegment]:
    return [segment for path in job.paths for segment in path.segments]


def _fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"
