# Plano de Implementacao - EPS SCARA Hotwire CutPlan

> **Plano histórico do MVP:** o [README](README.md) e o [guia do agente](docs/18_GUIA_AGENTE.md) descrevem a estrutura atual. G-code direto permanece desabilitado; resultados históricos não comprovam liberação atual.

Data: 2026-05-29

## Objetivo

Criar um repositorio para gerar pacotes de corte EPS/isopor para a SCARA CNC de fio quente/linha quente, usando Codex para estruturar pedidos em YAML e Python para validar e gerar DXF R12, preview, PDF, manifest e pacote de maquina.

Fluxo MVP:

```text
texto / foto / croqui / medidas
  -> Codex cria ou edita project.yaml
  -> Python valida schema, escala, bloco, maquina, fio e seguranca
  -> templates geram CutPath[] deterministico
  -> exportadores criam DXF R12 + SVG/PDF + manifest
  -> operador abre DXF no LazyCam
  -> LazyCam gera G-code
  -> Mach3/EPS faz dry-run e executa na SCARA
```

Router/fresa foi arquivado em `archive/router_spindle_eps/` e nao e fluxo ativo desta maquina.

## Validacao por docs oficiais

| Fonte oficial | Ponto validado | Decisao no repositorio |
| --- | --- | --- |
| [MachSupport - Mach3](https://www.machsupport.com/software/mach3/) | Mach3 controla motores processando G-code e usa perfis/configuracoes de maquina. | Preservar Mach3/EPS como controlador final e exigir backup antes de mexer no PC da maquina. |
| [MachSupport - LazyCam](https://www.machsupport.com/software/mach-3-add-ons-for-mill/) | LazyCam importa DXF/CMX para gerar G-code para Mach3, mas e beta. | Manter LazyCam como ponte do MVP, com checklist, escala/origem e dry-run obrigatorios. |
| [Autodesk - DXF R12 Reference](https://damassets.autodesk.net/content/dam/autodesk/www/developer-network/platform-technologies/autocad-dxf-archive/acad_r12_dxf.pdf) | DXF R12 e documentado por group codes, entidades e layers. | Exportar DXF R12 com allowlist de entidades simples. |
| [ezdxf r12writer](https://ezdxf.readthedocs.io/en/stable/addons/r12writer.html) | `r12writer` cria DXF R12 simples. | Usar `ezdxf` quando disponivel e fallback textual controlado. |
| [OpenAI Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md) | `AGENTS.md` orienta o Codex no repositorio. | Manter instrucoes curtas, operacionais e hotwire-first. |
| [OpenAI Codex Skills](https://developers.openai.com/codex/skills) | Skills empacotam instrucoes e referencias sob demanda. | Skill `eps-cnc-cutplan` foca SCARA/fio quente. |
| [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | JSON Schema reduz campos omitidos e enums invalidos. | `schemas/project_hotwire.schema.json` e o contrato do Codex. |
| [OpenCV Contours](https://docs.opencv.org/4.x/d4/d73/tutorial_py_contours_begin.html) | Contornos dependem de imagem binaria e pre-processamento. | Foto gera rascunho bloqueado ate escala e medidas confirmadas. |
| [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) | Draft oficial para contratos JSON Schema. | Criar schema tambem para `machine_profiles/scara_hotwire_eps.yaml`. |
| [python-jsonschema](https://python-jsonschema.readthedocs.io/en/stable/validate/) | `Draft202012Validator` valida schemas e instancias com `iter_errors`. | Validar perfil de maquina com mensagens de erro por caminho. |

## Decisoes vigentes

| Tema | Decisao |
| --- | --- |
| Processo ativo | `scara_hotwire_eps` / `hotwire_2d`. |
| Processo arquivado | Router/fresa em `archive/router_spindle_eps/`. |
| Fonte da verdade | `project.yaml` + `machine_profiles/scara_hotwire_eps.yaml`. |
| Unidade | Sempre mm. |
| Papel do Codex | Interpretar pedido/foto/medidas e editar YAML/codigo; nunca gerar DXF/G-code livre em texto. |
| Geometria final | `CutJobResult` e `CutPath[]` gerados por Python deterministico. |
| Formato principal | DXF R12 com entidades simples. |
| CAM/controle | LazyCam -> Mach3/EPS. |
| G-code direto | Experimental, bloqueado por padrao. |
| Foto | Sempre rascunho bloqueado ate escala e medidas confirmadas. |

## Estrutura ativa

```text
EPS/
  AGENTS.md
  README.md
  IMPLEMENTACAO_EPS_CNC.md
  VALIDACAO_OFICIAL_E_MELHORIAS.md

  docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md

  .codex/skills/eps-cnc-cutplan/
    SKILL.md
    references/workflow-scara-hotwire.md
    references/image-to-cutpath.md
    references/dxf-export-contract.md
    references/delivery-and-preview.md
    scripts/

  codex_contracts/
    prompt_text_to_hotwire_project.md
    prompt_image_to_draft_project.md
    prompt_review_project_yaml.md

  schemas/
    project_hotwire.schema.json
    machine_profile_hotwire.schema.json

  machine_profiles/
    scara_hotwire_eps.yaml
    scara_hotwire_teste.yaml

  projects/exemplos/
    001_linha_500mm.yaml
    002_quadrado_100mm.yaml
    003_grade_blocos_100mm.yaml
    005_foto_bloqueada.yaml
    007_tp40_nucleo_eps.yaml

  samples/real_machine/

  src/epscad/
    schema.py
    loader.py
    build.py
    templates/registry.py
    validators/geometry_validator.py
    validators/hotwire_validator.py
    validators/production_gate.py
    validators/schema_validator.py
    exporters/png_preview.py
    exporters/

  tests/
```

## Contrato hotwire minimo

```yaml
machine:
  profile: scara_hotwire_eps
  process_type: hotwire_2d
  output_format: dxf_r12
  cam_bridge: LazyCam
  controller_hint: Mach3_EPS

process:
  hotwire:
    wire_mode: line_hotwire
    wire_count: confirmar
    effective_kerf_mm: confirmar
    lead_in_mm: 20
    lead_out_mm: 20
    min_segment_mm: confirmar
    min_radius_mm: confirmar
  feed:
    xy_mm_min: confirmar
    slow_curve_mm_min: confirmar
```

Proibido no fluxo ativo da SCARA: fresa, spindle, RPM, Z seguro, profundidade por passe, pocket 2.5D e router.

## Estados de producao

| Estado | Pode gerar | Bloqueia |
| --- | --- | --- |
| `draft` | SVG/PDF preliminar | DXF producao e G-code |
| `validated_geometry` | DXF de teste | pacote final |
| `cam_ready` | pacote para LazyCam | G-code direto |
| `machine_tested` | pacote producao via LazyCam/Mach3 | G-code automatico |
| `production_released` | pacote final versionado | alteracoes sem nova revisao |

## Contrato DXF R12

Permitido no DXF de corte:

```text
LINE
ARC
CIRCLE
POLYLINE/VERTEX/SEQEND
geometria 2D no plano XY
```

Proibido no DXF final:

```text
SPLINE
HATCH
TEXT
MTEXT
DIMENSION
INSERT/BLOCK complexo
ELLIPSE
3DFACE
SOLID
entidade 3D
linha duplicada
segmento quase zero
```

## Validacoes obrigatorias

- `unit == mm`.
- Campos desconhecidos no YAML geram erro.
- Qualquer `confirmar` bloqueia producao.
- `machine.profile` precisa ser `scara_hotwire_eps`.
- `machine_profiles/scara_hotwire_eps.yaml` precisa passar no schema do perfil hotwire.
- `machine_profile_locked` precisa ser verdadeiro para `production_released`.
- Bounding box dentro da area util e do bloco EPS.
- Sem linhas duplicadas ou segmentos colineares duplicados.
- Sem segmentos menores que `min_segment_mm`.
- Sem spline ou entidade proibida no DXF.
- Preview/PDF deve mostrar origem, escala, bbox, status, bloco EPS, parametros do fio e checklist LazyCam/Mach3.
- Foto sem escala ou medidas confirmadas mantem `draft`.
- G-code exige fluxo experimental, golden samples, perfil travado e dry-run.
- Projeto SCARA com fresa, spindle, RPM, Z ou profundidade de passe deve falhar no schema.
- Em estados produtivos, `wire_count`, perda do fio, segmentos minimos e feeds precisam ser numericos validos.

## Ordem de implementacao

1. [feito] Reorientar repo para SCARA/fio quente como fluxo ativo.
2. [feito] Arquivar router/fresa fora do fluxo principal.
3. [feito] Atualizar `AGENTS.md`, README, docs, skill e contratos para hotwire-first.
4. [feito] Ajustar schema hotwire com `wire_mode`.
5. [feito] Adicionar teste que rejeita fresa/Z/RPM em projeto SCARA.
6. [feito] Manter testes hotwire e DXF passando.
7. [feito] Implementar `geometry_validator.py`: duplicidade, sobreposicao colinear, segmentos curtos, bbox contra estoque/area util e tolerancias.
8. [feito] Criar schema e validacao do perfil SCARA hotwire.
9. [feito] Validar campos numericos de hotwire em estados produtivos.
10. [feito] Criar docs de inventario da SCARA e backup do PC Mach3/EPS.
11. [feito] Criar preview PNG para entrega visual no Codex e pacote final.
12. [feito] Criar runbook `docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md`.
13. [feito] Melhorar PDF tecnico com preview cotado, aviso de nao-producao, dados hotwire e checklist LazyCam/Mach3.
14. [pendente] Preencher inventario real da SCARA e golden samples.
15. [feito] Git + publicacao em `hypeneural/eps`, `requirements.txt` e CI (`.github/workflows/ci.yml`).
16. [feito] DXF R12 completo (ezdxf + escritor reserva com HEADER/TABLES), ARC/CIRCLE exportados, validador DXF por secao.
17. [feito] Template `tp40_core` (miolo EPS telha TP40 trapezoidal) com exemplo, validacao, gate e testes. Ver `docs/11_TP40_TRAPEZOIDAL.md`.
18. [feito] Auditoria de prontidao: `docs/12_AUDITORIA_E_PRONTIDAO.md` (46 testes OK em 2026-11-24).

## Comandos de verificacao

```powershell
python .\scripts\validate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\generate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\validate_dxf.py .\outputs\001_linha_500mm\03_cutpaths_r12.dxf
python -m unittest discover -s tests -p "test_*.py"
```

## Checks executados - geometry_validator

```text
python -m unittest discover -s tests -p "test_*.py"
Resultado: 16 testes OK.

python scripts\validate_project.py projects\exemplos\001_linha_500mm.yaml
Resultado: errors=False.

python scripts\validate_project.py projects\exemplos\002_quadrado_100mm.yaml
Resultado: errors=False.

python scripts\validate_project.py projects\exemplos\003_grade_blocos_100mm.yaml
Resultado: errors=False.

python scripts\validate_project.py projects\exemplos\005_foto_bloqueada.yaml
Resultado: draft sem DXF de corte, com avisos esperados de confirmar/foto.

python scripts\validate_dxf.py outputs\001_linha_500mm\03_cutpaths_r12.dxf
Resultado: ok=True, entities=1, bbox=500 x 0 mm.

python scripts\validate_dxf.py outputs\002_quadrado_100mm\03_cutpaths_r12.dxf
Resultado: ok=True, entities=4, bbox=100 x 100 mm.

python scripts\validate_dxf.py outputs\003_grade_blocos_100mm\03_cutpaths_r12.dxf
Resultado: ok=True, entities=17, bbox=1000 x 500 mm.
```

Testes TDD adicionados:

- `geometry_duplicate_segment`: detecta segmento duplicado mesmo invertido.
- `geometry_segment_too_short`: bloqueia segmento menor que `min_segment_mm`.
- `geometry_outside_stock`: bloqueia bbox fora do bloco EPS.
- `geometry_outside_machine_area`: bloqueia bbox fora da area util quando o perfil tiver X/Y numericos.

## Checks executados - perfil e hotwire

```text
python -m unittest discover -s tests -p "test_machine_and_hotwire_gates.py"
Resultado: 5 testes OK.
```

Testes TDD adicionados:

- perfil `scara_hotwire_eps.yaml` passa no schema `machine_profile_hotwire.schema.json`;
- campo desconhecido no perfil da maquina gera erro;
- `process_type` diferente de `hotwire_2d` no perfil gera erro;
- estado produtivo rejeita strings nao numericas em perda do fio, segmentos e feed;
- estado produtivo rejeita `wire_count <= 0`.
