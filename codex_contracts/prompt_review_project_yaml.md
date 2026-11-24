# Contract - Revisao de Project YAML

Use quando o usuario pedir revisao de um `project.yaml`.

Checklist:

1. Confirmar `machine.profile=scara_hotwire_eps`.
2. Validar contra `schemas/project_hotwire.schema.json`.
3. Listar campos `confirmar`.
4. Verificar `source.kind`.
5. Verificar se foto sem escala esta bloqueada.
6. Verificar se `outputs.gcode.enabled=false`.
7. Verificar se `production_status` bate com os gates.
8. Sugerir somente mudancas no YAML, validators ou docs necessarias.

Nao alterar geometria de corte sem pedir/receber medidas reais.
Se aparecer fresa, spindle, RPM, Z, profundidade por passe ou `router`, bloquear como fluxo fora da SCARA atual.
