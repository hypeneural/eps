# Amostras Reais da Maquina

Guardar aqui exemplos reais do fluxo atual AutoCAD/LibreCAD/FreeCAD -> DXF -> LazyCam -> Mach3/EPS.

Estrutura recomendada:

```text
001_linha_500/
  original.dwg
  exportado.dxf
  lazycam_project.lcam
  mach3_gcode.tap
  foto_resultado.jpg
  medida_real.json
```

Minimo antes de qualquer G-code experimental:

- linha reta 500 mm;
- quadrado 100 x 100 mm;
- grade 5 x 5;
- arco simples.

Esses arquivos viram golden samples para conferir escala, origem, entidades DXF e dialeto real do Mach3.
