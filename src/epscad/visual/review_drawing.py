"""Scale-consistent technical image for nominal review (not a CAM drawing)."""
from PIL import Image, ImageDraw, ImageFont


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def write_section(roof, report, path):
    W, H = 1800, 780
    image = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(image)
    f_title = _font(22)
    f_sub = _font(16)
    f_body = _font(15)
    f_small = _font(14)

    width, height = report["width_mm"], report["height_mm"]
    geom = report.get("geometry") or {}

    # Main full-width uniform XY section
    scale = min(1520 / width, 240 / height)

    def p(x, y):
        return (120 + x * scale, 315 - y * scale)

    d.polygon([p(x, y) for x, y in roof.metal.exterior.coords], fill=(150, 162, 174), outline=(65, 76, 88), width=1)
    d.polygon([p(x, y) for x, y in roof.core.exterior.coords], fill=(232, 239, 244), outline=(52, 78, 100), width=2)
    d.line([p(x, y) for x, y in report["profile_points_mm"]], fill=(26, 101, 155), width=3)

    # Width dimension
    x0, _ = p(0, 0)
    x1, _ = p(width, 0)
    d.line([(x0, 330), (x0, 368)], fill="black", width=2)
    d.line([(x1, 330), (x1, 368)], fill="black", width=2)
    d.line([(x0, 352), (x1, 352)], fill="black", width=2)
    d.text(((x0 + x1) / 2 - 36, 360), f"{width:g} mm", fill="black", font=f_body)

    # Total height dimension (right side)
    _, y_bot = p(width, 0)
    _, y_top = p(width, height)
    d.line([(x1 + 14, y_top), (x1 + 48, y_top)], fill="black", width=2)
    d.line([(x1 + 14, y_bot), (x1 + 48, y_bot)], fill="black", width=2)
    d.line([(x1 + 32, y_top), (x1 + 32, y_bot)], fill="black", width=2)
    d.text((x1 + 52, (y_top + y_bot) / 2 - 8), f"{height:g} mm", fill="black", font=f_body)

    # Zoomed module + microgroove detail inset (if parametric geometry provided)
    if geom.get("pitch_mm") and geom.get("groove_width_mm") and geom.get("groove_depth_mm"):
        pitch = float(geom["pitch_mm"])
        rib = float(geom["rib_height_mm"])
        crest = float(geom["crest_span_mm"])
        valley = float(geom["valley_width_mm"])
        ramp = float(geom["ramp_run_mm"])
        gw = float(geom["groove_width_mm"])
        gd = float(geom["groove_depth_mm"])
        tmin = float(report["min_thickness_mm"])

        box = (120, 415, 1040, 710)
        d.rectangle(box, fill=(248, 250, 252), outline=(140, 154, 168), width=2)
        d.text(
            (138, 428),
            f"DETALHE DO MODULO ({pitch:g} mm) E MICRODOBRA CENTRAL ({gw:g} x {gd:g} mm)",
            fill=(25, 49, 72),
            font=f_sub,
        )

        zscale = min(760 / pitch, 175 / height)

        def pz(x, y):
            return (195 + x * zscale, 668 - y * zscale)

        mod_pts = [pt for pt in report["profile_points_mm"] if pt[0] <= pitch + 1e-6]
        mod_core = mod_pts + [(pitch, height), (0.0, height)]
        d.polygon([pz(x, y) for x, y in mod_core], fill=(232, 239, 244), outline=(52, 78, 100), width=2)
        d.line([pz(x, y) for x, y in mod_pts], fill=(26, 101, 155), width=3)

        # Highlight central microgroove step
        sh = (crest - gw) / 2.0
        gx0, gx1 = ramp + sh, ramp + sh + gw
        d.line([pz(gx0, rib), pz(gx0, rib - gd), pz(gx1, rib - gd), pz(gx1, rib)], fill=(200, 42, 42), width=4)
        gx_mid = (pz(gx0, rib - gd)[0] + pz(gx1, rib - gd)[0]) / 2
        d.text((gx_mid - 74, pz(gx0, rib - gd)[1] + 10), f"Microdobra {gw:g} x {gd:g} mm", fill=(180, 32, 32), font=f_body)

        # Key summary panel on the right
        panel = (1075, 415, 1680, 710)
        d.rectangle(panel, fill=(248, 250, 252), outline=(140, 154, 168), width=2)
        rows = [
            "DIMENSOES NOMINAIS (REVISAO)",
            f"Largura util: {width:g} mm ({geom.get('periods')} x {pitch:g} mm)",
            f"Altura total: {height:g} mm | EPS minimo: {tmin:g} mm",
            f"Altura da nervura: {rib:g} mm | Rampa horizontal: {ramp:g} mm",
            f"Crista larga: {crest:g} mm | Vale estreito: {valley:g} mm",
            f"Microdobra central: {gw:g} x {gd:g} mm",
            f"Area transversal: {report['area_mm2']:g} mm2",
            f"Comprimento visual: {report.get('extrusion_length_mm_assumed', 1000):g} mm (hipotese)",
            f"Chapa ref.: {report.get('metal_gauge_mm_assumed', 0.43):g} mm (negativo, sem colisao)",
        ]
        for idx, line in enumerate(rows):
            d.text(
                (1095, 430 + idx * 29),
                line,
                fill=(25, 49, 72) if idx == 0 else (35, 45, 55),
                font=f_sub if idx == 0 else f_body,
            )

    d.text((120, 26), "TP40 BASE LISA | SECAO NOMINAL - REVISAO, NAO CORTE", fill=(25, 49, 72), font=f_title)
    d.text(
        (120, 58),
        f"Altura {height:g} mm | EPS minimo {report['min_thickness_mm']:g} mm | Area {report['area_mm2']:g} mm2 | 5 modulos de {geom.get('pitch_mm', 196):g} mm",
        fill="black",
        font=f_sub,
    )
    d.text(
        (120, 735),
        "Perfil em escala XY uniforme com detalhe ampliado da microdobra. Dimensoes fisicas e encaixe ainda nao homologados.",
        fill=(60, 70, 80),
        font=f_small,
    )
    image.save(path)
