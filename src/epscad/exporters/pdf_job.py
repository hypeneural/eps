from __future__ import annotations

from pathlib import Path
from typing import Any

from epscad.schema import CutJobResult


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
PRODUCTION_RELEASED = "production_released"


def write_pdf_job(job: CutJobResult, spec: dict[str, Any], path: str | Path) -> None:
    """Write a single-page technical cut order PDF with uncompressed content."""
    ops: list[str] = []
    _draw_text_sections(ops, job, spec)
    _draw_preview(ops, job)
    _write_pdf(ops, Path(path))


def _draw_text_sections(ops: list[str], job: CutJobResult, spec: dict[str, Any]) -> None:
    y = 805
    _text(ops, 40, y, "ORDEM DE CORTE EPS - SCARA HOTWIRE", size=15, bold=True)
    y -= 22

    banner, detail = _status_banner(job, spec)
    _stroke_rect(ops, 38, y - 18, 519, 24, red=True)
    _text(ops, 48, y - 11, banner, size=11, bold=True, red=True)
    y -= 38
    _text(ops, 40, y, detail, size=9)
    y -= 24

    for line in _project_lines(job, spec):
        _text(ops, 40, y, line, size=9)
        y -= 13

    y -= 4
    _text(ops, 40, y, "Dados hotwire", size=10, bold=True)
    y -= 15
    for line in _hotwire_lines(spec):
        _text(ops, 40, y, line, size=9)
        y -= 13

    y -= 4
    _text(ops, 40, y, "Preview cotado", size=10, bold=True)
    y -= 15
    _text(ops, 40, y, _bbox_line(job), size=9)
    y -= 13
    _text(ops, 40, y, "Eixo X no preview: direita", size=9)
    y -= 13
    _text(ops, 40, y, "Eixo Y no preview: cima", size=9)
    y -= 22

    _text(ops, 40, y, "Checklist LazyCam", size=10, bold=True)
    y -= 15
    for line in _lazycam_checklist(job):
        _text(ops, 40, y, line, size=8.5)
        y -= 12

    y -= 4
    _text(ops, 40, y, "Checklist Mach3/EPS", size=10, bold=True)
    y -= 15
    for line in _mach3_checklist():
        _text(ops, 40, y, line, size=8.5)
        y -= 12

    if _photo_locked(spec):
        y -= 4
        _text(ops, 40, y, "Checklist de medidas pendentes", size=10, bold=True)
        y -= 15
        for line in _photo_pending_lines():
            _text(ops, 40, y, line, size=8.5)
            y -= 12

    if _tp40(job):
        _draw_tp40_section(ops, job)

    if job.validation:
        _text(ops, 318, 120, "Validacao", size=10, bold=True)
        _text(ops, 318, 104, f"Erros: {'sim' if job.has_errors else 'nao'}", size=8.5)
        _text(ops, 318, 92, f"Mensagens: {len(job.validation)}", size=8.5)


def _project_lines(job: CutJobResult, spec: dict[str, Any]) -> list[str]:
    material = spec.get("material", {})
    stock = material.get("stock", {})
    source = spec.get("project", {}).get("source", {})
    return [
        f"Projeto: {job.project_id}",
        f"Nome: {job.project_name}",
        f"Status: {job.production_status}",
        f"Maquina/perfil: {job.machine_profile}",
        f"Processo: {job.process_type}",
        f"Unidade: {job.unit}",
        f"Origem: {job.metadata.get('origin', '')}",
        f"Entrada: {source.get('kind', job.source_kind)}",
        f"Material: {material.get('type', '')}",
        f"Densidade: {material.get('density', '')}",
        f"Bloco EPS: X={_fmt_stock(stock.get('length_x'))} mm, Y={_fmt_stock(_stock_y(stock))} mm, Z={_fmt_stock(stock.get('thickness_z'))} mm",
    ]


def _hotwire_lines(spec: dict[str, Any]) -> list[str]:
    process = spec.get("process", {})
    hotwire = process.get("hotwire", {})
    feed = process.get("feed", {})
    cut = spec.get("cut", {})
    return [
        f"Modo do fio: {hotwire.get('wire_mode')}",
        f"Fios: {hotwire.get('wire_count')}",
        f"Kerf/perda efetiva: {hotwire.get('effective_kerf_mm')} mm",
        f"Lead-in: {hotwire.get('lead_in_mm')} mm",
        f"Lead-out: {hotwire.get('lead_out_mm')} mm",
        f"Segmento minimo: {hotwire.get('min_segment_mm')} mm",
        f"Raio minimo: {hotwire.get('min_radius_mm')} mm",
        f"Feed reto XY: {feed.get('xy_mm_min')} mm/min",
        f"Feed curva: {feed.get('slow_curve_mm_min')} mm/min",
        f"Compensacao: {cut.get('compensation')}",
    ]


def _lazycam_checklist(job: CutJobResult) -> list[str]:
    rows = [
        "- Abrir o DXF no LazyCam apenas depois de conferir esta ordem.",
        "- Conferir unidade em mm e escala 1:1.",
        "- Conferir origem e sentido X/Y antes de gerar G-code.",
        "- Conferir se nao ha linhas duplicadas ou cortes auxiliares.",
    ]
    if _dxf_allowed(job):
        rows.insert(0, "- Arquivo esperado: 03_cutpaths_r12.dxf.")
    else:
        rows.insert(0, "- DXF final nao liberado neste pacote.")
    return rows


def _mach3_checklist() -> list[str]:
    return [
        "- Abrir G-code gerado pelo LazyCam no perfil Mach3/EPS correto.",
        "- Conferir visualizacao, escala, origem e limites.",
        "- Dry-run obrigatorio com fio desligado ou sem material.",
        "- Primeiro corte deve ser em EPS de teste.",
        "- Registrar medida real para calibrar perda do fio.",
    ]


def _photo_pending_lines() -> list[str]:
    return [
        "- Informar uma medida real de referencia.",
        "- Confirmar escala pixel/mm antes de qualquer DXF.",
        "- Confirmar largura, altura e espessura do bloco EPS.",
        "- Sem DXF de producao enquanto escala e medidas nao forem confirmadas.",
    ]


def _status_banner(job: CutJobResult, spec: dict[str, Any]) -> tuple[str, str]:
    if _photo_locked(spec):
        return (
            "ARQUIVO PRELIMINAR - FOTO SEM ESCALA CONFIRMADA",
            "Sem DXF de producao enquanto escala e medidas nao forem confirmadas.",
        )
    if _tp40(job) and not _tp40(job).get("profile_confirmed"):
        return (
            "ARQUIVO PRELIMINAR - MEDIDAS TP40 NOMINAIS",
            "Medir a telha real e marcar profile_confirmed antes de liberar DXF.",
        )
    if job.production_status != PRODUCTION_RELEASED:
        return (
            "ARQUIVO DE TESTE - NAO CORTAR PRODUCAO",
            "Usar para conferencia, LazyCam e dry-run. Producao exige liberacao formal.",
        )
    return (
        "PRODUCAO LIBERADA - CONFERIR CHECKLIST",
        "Mesmo liberado, conferir escala, origem, fio e dry-run antes do corte.",
    )


def _draw_preview(ops: list[str], job: CutJobResult) -> None:
    x0 = 318
    y0 = 185
    width = 220
    height = 150
    _text(ops, x0, y0 + height + 18, "Preview geometrico", size=10, bold=True)
    _stroke_rect(ops, x0, y0, width, height)
    ops.append("% preview_vector_begin")
    if not job.paths:
        _text(ops, x0 + 48, y0 + 72, "Sem caminhos gerados", size=8)
        ops.append("% preview_vector_end")
        return

    bbox = _expanded_bbox(job.view_bbox)
    sx = width / bbox["width"]
    sy = height / bbox["height"]
    scale = min(sx, sy) * 0.85
    used_w = bbox["width"] * scale
    used_h = bbox["height"] * scale
    ox = x0 + (width - used_w) / 2 - bbox["min_x"] * scale
    oy = y0 + (height - used_h) / 2 - bbox["min_y"] * scale
    ops.append("0.65 0.65 0.65 RG")
    for segment in job.reference_segments:
        ops.append(
            f"{_n(ox + segment.start.x * scale)} {_n(oy + segment.start.y * scale)} m "
            f"{_n(ox + segment.end.x * scale)} {_n(oy + segment.end.y * scale)} l S"
        )
    _set_stroke_black(ops)
    for path in job.paths:
        for segment in path.segments:
            x1 = ox + segment.start.x * scale
            y1 = oy + segment.start.y * scale
            x2 = ox + segment.end.x * scale
            y2 = oy + segment.end.y * scale
            ops.append(f"{_n(x1)} {_n(y1)} m {_n(x2)} {_n(y2)} l S")

    origin_x = ox
    origin_y = oy
    ops.append("1 0 0 RG")
    ops.append(f"{_n(origin_x - 2)} {_n(origin_y - 2)} 4 4 re S")
    ops.append("0 0.45 0 RG")
    ops.append(f"{_n(origin_x)} {_n(origin_y)} m {_n(origin_x + 35)} {_n(origin_y)} l S")
    ops.append("0 0.1 1 RG")
    ops.append(f"{_n(origin_x)} {_n(origin_y)} m {_n(origin_x)} {_n(origin_y + 35)} l S")
    _set_stroke_black(ops)
    ops.append("% preview_vector_end")


def _tp40(job: CutJobResult) -> dict[str, Any]:
    return job.metadata.get("tp40") or {}


def _draw_tp40_section(ops: list[str], job: CutJobResult) -> None:
    tp = _tp40(job)
    y_range = tp.get("cut_line_y_range_mm", ["?", "?"])
    lines = [
        "Perfil TP40 trapezoidal (miolo EPS)",
        f"Confirmado: {'sim' if tp.get('profile_confirmed') else 'NAO - medidas nominais'}",
        f"Altura da onda: {tp.get('profile_height_mm')} mm",
        f"Passo: {tp.get('pitch_mm')} mm x {tp.get('n_waves')} ondas",
        f"Crista: {tp.get('crest_width_mm')} mm / Vale: {tp.get('valley_width_mm')} mm",
        f"Rampa: {tp.get('ramp_run_mm')} mm ({tp.get('ramp_angle_deg')} graus)",
        f"Espessura minima EPS: {tp.get('min_thickness_mm')} mm",
        f"Largura do painel: {tp.get('panel_width_mm')} mm",
        f"Linha de corte Y: {y_range[0]}..{y_range[1]} mm",
        f"Offset do fio: {tp.get('kerf_offset_mm')} mm",
        "Acima da linha: miolo / abaixo: contra-forma",
    ]
    y = 700
    for index, line in enumerate(lines):
        _text(ops, 318, y, line, size=9 if index == 0 else 8, bold=index == 0)
        y -= 14 if index == 0 else 12


def _bbox_line(job: CutJobResult) -> str:
    bbox = job.bbox
    return (
        f"BBox: X {_fmt_bbox(bbox['min_x'])}..{_fmt_bbox(bbox['max_x'])} mm / "
        f"Y {_fmt_bbox(bbox['min_y'])}..{_fmt_bbox(bbox['max_y'])} mm"
    )


def _expanded_bbox(bbox: dict[str, float]) -> dict[str, float]:
    result = dict(bbox)
    if result["width"] <= 0:
        center = (result["min_x"] + result["max_x"]) / 2
        result["min_x"] = center - 1
        result["max_x"] = center + 1
        result["width"] = 2
    if result["height"] <= 0:
        center = (result["min_y"] + result["max_y"]) / 2
        result["min_y"] = center - 1
        result["max_y"] = center + 1
        result["height"] = 2
    return result


def _photo_locked(spec: dict[str, Any]) -> bool:
    source = spec.get("project", {}).get("source", {})
    return (
        source.get("kind") == "image_reference"
        and not (source.get("scale_confirmed") and source.get("dimensions_confirmed"))
    )


def _dxf_allowed(job: CutJobResult) -> bool:
    return job.production_status in {"validated_geometry", "cam_ready", "machine_tested", "production_released"} and not job.has_errors


def _stock_y(stock: dict[str, Any]) -> Any:
    return stock.get("height_y", stock.get("width_y"))


def _fmt_stock(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _fmt_bbox(value: float) -> str:
    return f"{float(value):.1f}"


def _n(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _text(ops: list[str], x: float, y: float, text: str, *, size: float, bold: bool = False, red: bool = False) -> None:
    color = "1 0 0 rg" if red else "0 0 0 rg"
    font = "F2" if bold else "F1"
    ops.append(color)
    ops.append(f"BT /{font} {_n(size)} Tf {_n(x)} {_n(y)} Td ({_escape_pdf_text(text)}) Tj ET")


def _stroke_rect(ops: list[str], x: float, y: float, width: float, height: float, *, red: bool = False) -> None:
    if red:
        ops.append("1 0 0 RG")
    else:
        _set_stroke_black(ops)
    ops.append(f"{_n(x)} {_n(y)} {_n(width)} {_n(height)} re S")
    _set_stroke_black(ops)


def _set_stroke_black(ops: list[str]) -> None:
    ops.append("0 0 0 RG")


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _write_pdf(ops: list[str], path: Path) -> None:
    stream = "\n".join(ops)
    stream_bytes = stream.encode("latin-1")
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
            f"{PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream",
    ]
    content = "%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content.encode("latin-1")))
        content += f"{index} 0 obj\n{obj}\nendobj\n"
    xref_start = len(content.encode("latin-1"))
    xref = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    xref.extend(f"{offset:010d} 00000 n " for offset in offsets[1:])
    trailer = (
        "\n".join(xref)
        + "\n"
        + f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    )
    path.write_bytes((content + trailer).encode("latin-1"))
