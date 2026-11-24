# Analise Detalhada - Melhorias para Codex

Data: 2026-05-29

## Direcao atual

O repositorio deve ser simples para o Codex: sempre assumir SCARA CNC de fio quente/linha quente, gerar YAML validado e deixar Python produzir DXF R12 e pacote de conferencia.

Fluxo:

```text
pedido / foto / croqui
  -> Codex edita YAML
  -> schema hotwire valida
  -> validators bloqueiam risco
  -> templates geram CutPath[]
  -> exporters geram SVG/PDF/DXF/manifest
  -> LazyCam/Mach3 validam antes de corte
```

## Regras para reduzir ambiguidade

- Usar apenas `machine.profile=scara_hotwire_eps`.
- Usar apenas `machine.process_type=hotwire_2d`.
- Usar `schemas/project_hotwire.schema.json`.
- Incluir `process.hotwire.wire_mode`.
- Manter `outputs.gcode.enabled=false`.
- Usar `confirmar` para dado fisico nao medido.
- Bloquear producao se houver `confirmar`.
- Foto sem escala fica `draft`.

## Proibido no fluxo ativo

- fresa;
- spindle;
- RPM;
- Z seguro;
- profundidade por passe;
- pocket 2.5D;
- router.

Esses conceitos estao arquivados fora do fluxo ativo.

## Estrutura Codex

```text
AGENTS.md
.codex/skills/eps-cnc-cutplan/SKILL.md
codex_contracts/prompt_text_to_hotwire_project.md
codex_contracts/prompt_image_to_draft_project.md
codex_contracts/prompt_review_project_yaml.md
schemas/project_hotwire.schema.json
tests/
```

## Evals ativos

- texto hotwire -> YAML com `gcode.enabled=false`;
- foto -> draft bloqueado;
- tentativa de G-code direto -> rejeicao;
- SCARA com fresa/Z/RPM -> erro de schema.

## Proximos testes uteis

- `hotwire_requires_wire_mode`;
- `scara_rejects_router_fields`;
- `image_reference_writes_no_dxf`;
- `dxf_no_forbidden_entities`;
- `grid_blocks_no_duplicate_segments`;
- `confirmar_blocks_production`.
