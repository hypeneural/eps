---
name: eps-tp40-engineering
description: Analisa medidas TP40 trapezoidal, perfil negativo da chapa, EPS, kerf e geometria XY industrial.
---
# Engenharia
Leia docs/11_TP40_TRAPEZOIDAL.md, docs/13_TP40_3D_REMOTE.md e docs/16_DEVELOPMENT_HANDOFF.md. Use `python scripts/generate_catalog.py --list` como ponto de entrada unico de catalogos em `catalogs/roof_profiles/` para nunca confundir o perfil com microdobras (`tp40_980_microgroove_review`) com os catalogos trapezoidais simplificados (`tp40_980_sks`, `tp40_1020_isoeste`). Compare passo, crista, vale, altura, largura, fase, bordas, microdobras e espessura na face interna de contato. Registre medidas reais antes de liberar DXF de teste. Use `templates/tp40.py`, `geometry/roof.py` e `geometry/roof_review.py`; nao redesenhe pela imagem. Shapely valida poligonos; Trimesh e Earcut extrudam.
