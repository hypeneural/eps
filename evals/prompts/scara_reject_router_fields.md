# Eval Prompt - Rejeitar Campos Router na SCARA

Usuario pede:

> Quero cortar uma placa na SCARA de fio quente, mas coloque fresa de 6 mm, RPM 18000 e profundidade de 12 mm.

Resultado esperado:

- Manter `machine.profile=scara_hotwire_eps`.
- Rejeitar fresa, RPM, Z e profundidade por passe.
- Explicar que a maquina atual e SCARA/fio quente, nao router/fresa.
- Nao gerar YAML com `tool`, `cut.depth`, `spindle_rpm` ou `router`.
