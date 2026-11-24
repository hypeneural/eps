# Contract - Texto para Projeto Router

Use quando o usuario pedir corte de EPS com router/fresa.

Saida esperada do Codex:

- Criar ou editar YAML compativel com `schemas/project_router.schema.json`.
- Usar `machine.profile=router_eps`.
- Usar `machine.process_type=router_spindle`.
- Exigir `tool.kind`, `tool.diameter_mm`, `tool.effective_kerf_mm`, `tool.flute_length_mm`.
- Exigir `cut.depth.z_safe_mm`, `cut.depth.final_depth_z`, `cut.depth.pass_depth_mm`.
- Exigir `cut.feed.xy_mm_min`, `cut.feed.z_mm_min`, `cut.feed.spindle_rpm`.
- Manter `outputs.gcode.enabled=false`.

Proibido:

- Gerar DXF/G-code diretamente.
- Inventar Z seguro, RPM, feed, fresa ou profundidade por passe.
- Marcar producao liberada se ferramenta/Z/feed/RPM estiverem em `confirmar`.
