# Schema Rules

- `additionalProperties` deve continuar `false`.
- Todo campo novo exige validator correspondente.
- Toda enum nova exige teste.
- Os schemas ativos sao `project_hotwire.schema.json` e `machine_profile_hotwire.schema.json`.
- Nao adicionar campos de fresa, Z, RPM, spindle, pocket ou profundidade de passe ao fluxo SCARA/fio quente.
- `outputs.gcode.enabled` deve continuar `false` nos schemas MVP.
- Campo novo em schema exige exemplo YAML e contrato em `codex_contracts/`.
