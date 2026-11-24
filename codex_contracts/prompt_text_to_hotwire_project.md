# Contract - Texto para Projeto Hotwire

Use quando o usuario pedir corte para SCARA/fio quente por texto.

Saida esperada do Codex:

- Criar ou editar YAML compativel com `schemas/project_hotwire.schema.json`.
- Usar `machine.profile=scara_hotwire_eps`.
- Usar `machine.process_type=hotwire_2d`.
- Usar `process.hotwire.wire_mode=line_hotwire`, salvo quando o operador confirmar outro modo real.
- Manter `project.unit=mm`.
- Manter `outputs.gcode.enabled=false`.
- Usar `confirmar` para dado fisico da maquina nao informado.
- Manter `production_confirmed=false` ate validacao humana.

Proibido:

- Gerar DXF diretamente.
- Inventar area util, origem, velocidade, perda do fio ou quantidade de fios.
- Usar fresa, spindle, RPM, Z seguro, profundidade por passe, pocket ou router para a maquina SCARA atual.
- Marcar `production_released` se houver `confirmar`.
