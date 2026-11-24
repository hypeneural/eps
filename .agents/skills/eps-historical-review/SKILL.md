---
name: eps-historical-review
description: Analisa DXF/TAP histórico e ZIP de evidências da fábrica para reconstrução geométrica e comparação; use somente em revisão local.
---

# Procedimento
Leia docs/15_HISTORICAL_EVIDENCE.md. Preserve originais em private_evidence/; não executar TAP/macros. Identifique unidades, versão, entidades, sobreposição e limites CAD selecionados. Para referência TP40 base lisa use scripts/prepare_tp40.py --evidence <ZIP> --output <pasta-nova>; sem ZIP, reporte referência normalizada não recomparada. Para outro perfil LINE use scripts/review_historical_roof.py --help, limites e topo explicitamente conferidos. Não assumir que a trajetória é o contorno da peça, nem apagar retornos de fio. Compare seção, diferença simétrica, área e preview. Entrega visual apenas; nenhuma autorização de corte ou publicação dos originais.
