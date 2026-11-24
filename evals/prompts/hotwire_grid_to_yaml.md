# Eval Prompt - Hotwire Grid to YAML

Usuario pede:

> Quero cortar uma grade de blocos de EPS 100 x 100 mm na SCARA/fio quente, bloco 1000 x 500 mm.

Resultado esperado:

- Usar `machine.profile=scara_hotwire_eps`.
- Usar `machine.process_type=hotwire_2d`.
- Usar `process.hotwire.wire_mode=line_hotwire`.
- Usar `template=grid_blocks`.
- Manter `unit=mm`.
- Manter `outputs.gcode.enabled=false`.
- Usar `confirmar` para perda de fio, velocidade e area util se nao informadas.
