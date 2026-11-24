# EPS SCARA Hotwire Agent Guide

Este repositorio gera pacotes de corte EPS/isopor para a SCARA CNC de fio quente/linha quente usando DXF R12, LazyCam e Mach3/EPS.

## Regras obrigatorias

- Trabalhar sempre em milimetros.
- A fonte da verdade e `project.yaml` + `machine_profiles/scara_hotwire_eps.yaml`.
- O unico processo ativo e `machine.profile=scara_hotwire_eps` com `process_type=hotwire_2d`.
- Nao tratar a maquina atual como router/fresa.
- Nao usar spindle, RPM, fresa, diametro de ferramenta, Z seguro, profundidade por passe, pocket 2.5D ou router no fluxo ativo.
- Nunca inventar area util, origem, eixo, velocidade, perda do fio, formato aceito ou quantidade de fios.
- Qualquer campo `confirmar`, `null` tecnico ou `profile_locked=false` bloqueia producao.
- Foto/imagem nunca libera corte final sem escala e medidas reais confirmadas.
- Codex edita YAML e codigo; nao gera DXF ou G-code livre em resposta textual.
- DXF de corte sai do exportador Python.
- DXF de producao deve ser R12 com entidades simples e sem texto/cotas.
- G-code direto e experimental e bloqueado por padrao.
- Todo template novo precisa de exemplo YAML, validacao e teste.
- Toda mudanca que afeta corte precisa atualizar manifest, checklist/PDF e testes.

## Ordem obrigatoria do Codex

1. Ler `docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md` quando a tarefa envolver fluxo, outputs ou entrega.
2. Confirmar `machine.profile=scara_hotwire_eps`.
3. Validar contra `schemas/project_hotwire.schema.json`.
4. Validar YAML antes de alterar templates/exportadores.
5. Rodar ou planejar `validate_project`.
6. Gerar pacote somente se nao houver erro.
7. Rodar ou planejar `validate_dxf`.
8. Rodar testes.
9. Atualizar `docs/DECISOES_TECNICAS.md` se mudar regra de maquina, CAM, DXF ou seguranca.

## Regras SCARA/fio quente

- Exigir `process.hotwire.wire_mode`, `wire_count`, `effective_kerf_mm`, `min_segment_mm`, `min_radius_mm` e feed XY.
- Bloquear producao se perda do fio, origem, eixo, velocidade ou quantidade de fios estiverem em `confirmar`.
- Foto sempre vira `draft` ate escala e dimensoes confirmadas.
- LazyCam/Mach3 continuam como fluxo real; sempre exigir checklist e dry-run antes de corte.

## DXF permitido

Permitido no DXF de corte:

- `LINE`
- `ARC`
- `CIRCLE`
- `POLYLINE`, `VERTEX`, `SEQEND`

Proibido no DXF de corte:

- `SPLINE`
- `HATCH`
- `TEXT`
- `MTEXT`
- `DIMENSION`
- `INSERT`/`BLOCK` complexo
- `ELLIPSE`
- `3DFACE`
- `SOLID`
- entidades 3D

## Docs principais

- `IMPLEMENTACAO_EPS_CNC.md`: plano de implementacao hotwire-first.
- `docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md`: runbook operacional do Codex e entrega visual.
- `VALIDACAO_OFICIAL_E_MELHORIAS.md`: fontes oficiais e melhorias obrigatorias.
- `ANALISE_MDF_PARA_EPS_CNC.md`: adaptacao historica da arquitetura MDF para EPS CNC.
- `docs/DECISOES_TECNICAS.md`: decisoes tecnicas vigentes.

Router/fresa esta arquivado em `archive/router_spindle_eps/` e nao deve ser usado no fluxo ativo da SCARA.

## Comandos esperados

```powershell
python .\scripts\validate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\generate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\validate_dxf.py .\outputs\001_linha_500mm\03_cutpaths_r12.dxf
python -m unittest discover -s tests -p "test_*.py"
```

## Done significa

- `project.yaml` passa no schema hotwire.
- Nenhum campo `confirmar` e usado para producao.
- `validate_project` passa.
- `generate_project` gera manifest, PDF, SVG e DXF quando o status permite.
- `generate_project` gera `01_preview.png` para visualizacao direta.
- `02_ordem_corte_eps.pdf` mostra alerta de status, bloco EPS, parametros do fio, bbox e checklist LazyCam/Mach3.
- `validate_dxf` nao encontra entidade proibida.
- Testes passam.
- Mudanca em saida de maquina atualiza checklist, PDF e manifest.
