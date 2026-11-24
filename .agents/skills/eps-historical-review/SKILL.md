---
name: eps-historical-review
description: Audita DXF historico de EPS e recupera geometria nominal para STL GLB e render sem liberar corte.
---
Leia docs/15_HISTORICAL_EVIDENCE.md. Mantenha evidencias em private_evidence/. Inspecione versao, unidades, entidades, extensoes e sobreposicao. Use scripts/review_historical_roof.py apenas com limites CAD explicitos e topo plano conferido. Compare preview e desenho original. Nao assumir que TAP historico foi executado com sucesso. Nao gerar TAP nem DXF de corte deste fluxo.

Para o primeiro modelo TP40 base lisa, leia docs/16_DEVELOPMENT_HANDOFF.md e execute scripts/prepare_tp40.py. Nao depende de acesso ao PC da fabrica. ZIP opcional via --evidence ou private_evidence/MACROS_CNC_V.zip. Validar comparacao e imagens, nunca liberar corte.
