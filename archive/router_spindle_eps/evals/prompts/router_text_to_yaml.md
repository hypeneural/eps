# Eval Prompt - Router Text to YAML

Usuario pede:

> Preciso cortar uma letra de isopor na router usando fresa de 6 mm, bloco 1000 x 500 x 100 mm. Ainda nao sei RPM, feed e Z seguro.

Resultado esperado:

- Usar `machine.profile=router_eps`.
- Usar `machine.process_type=router_spindle`.
- Incluir ferramenta de 6 mm.
- Marcar RPM, feed e Z seguro como `confirmar`.
- Manter `outputs.gcode.enabled=false`.
- Manter status `draft` ou equivalente nao produtivo.
