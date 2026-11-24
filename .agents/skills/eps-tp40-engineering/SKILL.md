---
name: eps-tp40-engineering
description: Gera ou altera perfil TP40 de EPS a partir de catálogo e medidas; use para base lisa, microdobras, negativo metálico, espessura e malhas.
---

# Escolha do gerador
- Ponto de entrada único por catálogo: `python scripts/generate_catalog.py --list` e `python scripts/generate_catalog.py <catalog_id> --output <pasta>` roteia automaticamente sem misturar perfis.
- Base lisa histórica com microdobras (`tp40_980_microgroove_review`): `scripts/prepare_tp40.py --help`; catálogo `tp40_980_microgroove_review.yaml`. Referência de 980 × 67 mm, 31 mm mínimos, 5 módulos de 196, microdobra 48 × 2, área 42560 mm² no baseline. Leia `docs/16_DEVELOPMENT_HANDOFF.md`.
- TP40/980 SKS ou TP40/1020 Isoeste simplificada: `scripts/new_tp40.py --help`; leia `docs/11_TP40_TRAPEZOIDAL.md` e `docs/13_TP40_3D_REMOTE.md`.
- Foto sem medidas: draft, sem DXF. Evidência histórica: `eps-historical-review`.

# Execução
Escolha ID explícito; não misture perfis. Comprimento e bitola de referência não são medidas homologadas. Use scripts existentes, Shapely/Trimesh/Earcut. Verifique área, volume, cinco microdobras e invariância da interface ao mudar espessura mínima. Não alterar geometria para melhorar estética. Compare relatório e hashes, registre hipóteses, não liberar corte.
