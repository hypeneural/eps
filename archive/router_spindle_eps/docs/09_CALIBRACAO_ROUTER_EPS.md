# Calibracao Router EPS

Data: 2026-05-29

## Objetivo

Registrar testes minimos antes de liberar `router_eps` para producao.

## Testes obrigatorios

1. Dry-run sem fresa ou com Z seguro alto, usando linha 500 mm.
2. Quadrado 100 x 100 mm em EPS barato.
3. Circulo/arco simples para validar interpolacao no CAM/controlador.
4. Grade 5 x 5 para validar escala e repetibilidade.
5. Pocket raso para validar profundidade por passe, feed Z e acabamento.
6. Through-cut com overcut controlado para validar profundidade final.

## Medicoes

Registrar em `samples/real_machine/<teste>/medida_real.json`:

```json
{
  "tool_diameter_mm": 6,
  "programmed_width_mm": 100,
  "measured_width_mm": 99.4,
  "programmed_depth_mm": 10,
  "measured_depth_mm": 9.8,
  "feed_xy_mm_min": 1200,
  "feed_z_mm_min": 300,
  "spindle_rpm": 18000,
  "notes": ""
}
```

## Criterios de bloqueio

- Medida real fora da tolerancia definida.
- Queima/fusao excessiva do EPS.
- Vibracao, arrancamento ou acabamento ruim.
- CAM aplicando compensacao duplicada.
- Z final atravessando mesa/suporte.
- Falta de registro de ferramenta, feed, RPM ou profundidade.
