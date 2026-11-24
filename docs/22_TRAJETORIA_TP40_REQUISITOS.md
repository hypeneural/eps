# Auditoria da Trajetória Industrial TP40 Base Lisa — Requisitos para Futura Homologação Física

Data: 2026-11-24  
Branch CAD: `feat/tp40-3d-industrial-package`  
Status: **Especificação técnica pré-homologação (SEM geração de DXF comercial, SEM G-code direto, perfil SCARA permanece bloqueado)**

> **Separação obrigatória:** geometria nominal do núcleo EPS (`980 × 67 mm`, 5 módulos de `196 mm`, 5 microdobras de `48 × 2 mm`, área `42.560 mm²`) **não equivale** ao percurso real do fio quente. Este documento registra achados forenses da auditoria local sobre a evidência histórica (`private_evidence/MACROS_CNC_V.zip`, fora do Git) e define os requisitos objetivos necessários antes de implementar e homologar um futuro template de corte da TP40 base lisa.

---

## 1. Achados Forenses: Geometria Nominal vs. Trajetória Histórica

Comparação analítica (somente leitura) entre a seção nominal recuperada (`catalogs/roof_profiles/tp40_980_microgroove_review.yaml`) e o par histórico `telha tp 40 base lisa.dxf` / `telha tp 40 base lisa.tap` presente no acervo local privado:

| Aspecto | Geometria Nominal (Produto) | Evidência Histórica (DXF / TAP) | Implicação de Engenharia |
| --- | --- | --- | --- |
| Envelope XY | `980,0 × 67,0 mm` (`X ∈ [0, 980]`, `Y ∈ [0, 67]`) | DXF em `X=[146,3136..1132,3136]`, `Y=[55,5384..122,5384]` (`986,0 × 67,0 mm`); TAP deslocado para `X=[0..986]`, `Y=[0..67]` | Diferença de `+6 mm` em X corresponde a entrada e esquadrejamento à esquerda; origem real da máquina deve ser confirmada fisicamente. |
| Comprimento da interface / trajeto | Interface única monotônica: `1.158,365 mm` (com esquadrejamento esquerdo/direito simples: `~1.297 mm`) | `50` entidades `LINE` (`3.005,365 mm` totais no DXF e no TAP; comprimento único sem sobreposições = `2.185,365 mm`) | O trajeto histórico percorre **2,59×** o comprimento da interface nominal devido a retornos e sobreposições colineares em `Y=0`. |
| Entradas e saídas | Não fazem parte da geometria nominal | Entrada horizontal `5 mm` em `Y=0` (`0->5`), laço vertical de `1 mm` de largura (`(5,0)->(5,67)->(6,67)->(6,0)`), saída vertical direita `(986,0)->(986,67)` | LazyCam histórico tem `AutoLead=0`. O laço de `1 mm` é mais estreito que a perda térmica típica (`1,5–3,0 mm`), podendo derreter a tira fina; exigir política explícita de `lead_in`/`lead_out` e esquadrejamento. |
| Retornos e sobreposições | Zero retornos (`+X` monotônico) | `21` segmentos com movimento `-X`; `11` segmentos na base `Y=0` somando `1.805 mm` sobre um vão de `986 mm` (`820 mm` = `5 × 164 mm` de sobreposição colinear em `Y=0`) | Cada onda é percorrida em laço fechado sobre `Y=0` (módulos 2–5 cortados em reverso `-X` após avanço de `+164 mm` na base e retorno de `+196 mm`), gerando passagem dupla/tripla do fio quente sobre o plano inferior e risco de sobre-queima nos vales de `32 mm`. |
| Menor segmento | Degrau vertical da microdobra: `2,0 mm` (`48 × 2 mm`) | Menor segmento no TAP: `1,0 mm` (topo do laço esquerdo) e `2,0 mm` (10 degraus verticais das microdobras) | Qualquer futuro perfil SCARA precisa confirmar se `min_segment_mm <= 2,0 mm` é fisicamente viável sem arredondamento térmico excessivo. |
| Códigos modais e parâmetros | Não aplicável à geometria | TAP contém `G21`, `G80`, `G4`, `M3`, `M5`, `M30`, `G1`, `F600`, `S300` — **ausência de `G90` explícito** no cabeçalho | `F600` e `S300` históricos **não são parâmetros autorizados**. Ausência de `G90` (coordenadas absolutas) representa risco modal se a controladora estiver em `G91`. |

### Comparação com Outros Perfis TP40 do Acervo Histórico
- **`TP40 palhoça.tap`** (`980 × 37 mm`, `1.250,34 mm`, `0` movimentos `-X`) e **`telha tp 40 5 cm.tap`** (`980 × 55 mm`, `1.287,96 mm`, `0` movimentos `-X`): utilizam corte contínuo monotônico esquerda-direita sem sobreposição em `Y=0`.
- **`telha tp 40 base lisa.tap`** (`986 × 67 mm`, `3.005,365 mm`, `21` movimentos `-X`): apresenta fechamento inferior dos 5 bolsões trapezoidais (`5 × 164 mm`). Antes de definir o modo de corte definitivo, o operador precisa confirmar fisicamente na fábrica se o bloco entra pré-fatiado em `67 mm` (onde um único corte monotônico contínuo basta) ou em bloco alto (onde a separação dos bolsões ou um corte plano auxiliar é necessária).

---

## 2. Requisitos Obrigatórios para Futuro Template de Trajetória TP40 Base Lisa

Nenhum DXF comercial da TP40 base lisa pode ser liberado enquanto **todos** os requisitos abaixo não forem atendidos:

1. **Separação estrita entre modelo nominal e trajetória (`cutpath`):**
   - A seção nominal (`catalogs/roof_profiles/tp40_980_microgroove_review.yaml`) gera apenas conferência (STL mm, GLB m, PNG técnico, renders Cycles, `TP40_REVISAO.zip`).
   - Um futuro template de corte deve operar sobre uma camada de trajetória explícita (`lead_in` -> corte monotônico contínuo sem sobreposições colineares em `Y=0` -> `lead_out` opcional / esquadrejamento configurado), mantendo a geometria nominal intacta apenas como referência visual (`REF_NOMINAL`).
2. **Proibição de sobreposição térmica não declarada:**
   - Trajetórias geradas pelo motor devem ter `0` segmentos duplicados e `0` sobreposições colineares de fio quente sobre faces acabadas (como os `820 mm` sobrepostos em `Y=0` no histórico), salvo modo explicitamente modelado e validado fisicamente.
3. **Compensação térmica (`effective_kerf_mm`) segura nas microdobras (`48 × 2 mm`):**
   - O offset de meio kerf (`k/2`) desloca as paredes verticais de `2 mm` e o fundo de `48 mm`.
   - Condição geométrica obrigatória sem auto-interseção nem colapso do degrau:
     - `effective_kerf_mm > 0` medido em corpo de prova real;
     - `effective_kerf_mm / 2 < groove_depth_mm` (`k < 4,0 mm` para degrau de `2,0 mm`, preservando margem positiva);
     - `effective_kerf_mm < groove_width_mm` (`k < 48,0 mm`);
     - `effective_kerf_mm < valley_width_mm` (`k < 32,0 mm`);
     - `offset_polyline` não pode produzir auto-interseção, inversão de segmento ou saída dos limites do bloco (`0 <= x <= stock_x`, `0 <= y <= stock_y`).
   - Avaliar fisicamente se o degrau de `2 mm` absorve o próprio raio térmico do fio sem exigir sobre-compensação ou se exige ajuste de profundidade/largura confirmado em corpo de prova.
4. **Entradas, saídas e limites de máquina (`machine_profiles/scara_hotwire_eps.yaml`):**
   - Confirmar `work_area.x_max >= panel_width_mm + lead_in_mm + lead_out_mm` (ex.: `>= 1.020 mm` com `20 mm` de entrada e saída) e `work_area.y_max >= total_height_mm + stock_margin`.
   - Confirmar `axes.x_positive`, `axes.y_positive`, `zero_policy`, `home_policy`, `wire_count`, `min_segment_mm` (`<= 2,0 mm` para preservar microdobras), `default_xy_mm_min` e `slow_curve_mm_min`.
   - Como o LazyCam histórico usa `AutoLead=0`, qualquer entrada/saída horizontal ou vertical necessária deve ser explicitada no DXF R12 (`LINE` contínuo em `CUT_OUTSIDE`) e conferida visualmente no LazyCam antes de gerar TAP na fábrica.
5. **Verificação de continuidade e importação LazyCam/Mach3:**
   - DXF R12 (`AC1009`), somente entidades `LINE`, encadeamento contínuo ponto-a-ponto (tolerância `<= 0,001 mm`), direção única validada (`+X`), escala 1:1 confirmada no LazyCam Foam, `G21`/`G90` conferidos no Mach3 da fábrica, **dry-run sem aquecimento** e primeiro corte supervisionado em EPS de teste.
6. **Contrato de liberação V3:**
   - Somente após homologação física e `profile_locked: true` (preenchido com medidas reais da fábrica), emitir pacote `production_released`, conferir hashes via `scripts/check_release_candidate.py` (`dxf_sha256`, `project_sha256`, `profile_sha256`) e registrar aprovação humana explícita.

---

## 3. Testes Automatizados de Pré-Requisito (`tests/test_tp40_cutpath_requirements.py`)

Foram adicionados testes determinísticos sobre geometria sintética da seção TP40 base lisa validando:
- Continuidade monotônica `+X` sem retornos `-X` nem sobreposições colineares na interface nominal (`1.158,3646 mm`).
- Invariância dos 5 módulos e 5 microdobras `48 × 2 mm` sob variação de `min_thickness_mm`.
- Limite geométrico seguro de compensação térmica (`offset_polyline`) para `kerf` realista (`1,0`–`3,0 mm`), rejeição de colapso quando `kerf/2 >= groove_depth_mm`, e verificação de envelopes com `lead_in`/`lead_out`.
- Bloqueio contínuo do perfil real `machine_profiles/scara_hotwire_eps.yaml` (`profile_locked=false`) e ausência total de DXF/G-code no pacote de revisão `prepare_tp40.py`.
