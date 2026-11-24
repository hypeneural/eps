# Inventario da Maquina SCARA

Data: 2026-05-29

Este documento deve ser preenchido antes de liberar `production_released`. Enquanto houver `confirmar`, o perfil da maquina continua bloqueado.

## Identificacao

| Item | Valor | Como confirmar | Status |
| --- | --- | --- | --- |
| Nome da maquina | SCARA CNC EPS fio quente | placa, tela Mach3 ou documentacao local | pendente |
| Controlador | Mach3/EPS | tela/perfil do Mach3 | pendente |
| Ponte CAM | LazyCam | fluxo atual do operador | pendente |
| Formato principal | DXF R12 | teste de importacao no LazyCam | pendente |

## Area util e eixos

| Item | Valor | Como medir | Status |
| --- | ---: | --- | --- |
| Area util X | confirmar | medir curso real ou limite no Mach3 | pendente |
| Area util Y | confirmar | medir curso real ou limite no Mach3 | pendente |
| Altura/espessura util Z | confirmar | medir curso/espessura suportada | pendente |
| X positivo | confirmar | jog manual em baixa velocidade | pendente |
| Y positivo | confirmar | jog manual em baixa velocidade | pendente |
| Politica de zero | confirmar | observar preparacao de corte real | pendente |
| Politica de home | confirmar | observar homing/ref all no Mach3 | pendente |

## Fio quente

| Item | Valor | Como medir | Status |
| --- | ---: | --- | --- |
| Modo do fio | line_hotwire | inspecao fisica/tela EPS | pendente |
| Quantidade de fios ativos | confirmar | inspecao fisica e teste de corte | pendente |
| Perda efetiva do fio mm | confirmar | quadrado 100 x 100 mm medido | pendente |
| Segmento minimo mm | confirmar | teste de microsegmentos seguro | pendente |
| Raio minimo mm | confirmar | teste de arco simples | pendente |
| Lead-in padrao mm | 20 | validar em corte teste | pendente |
| Lead-out padrao mm | 20 | validar em corte teste | pendente |

## Feed e seguranca

| Item | Valor | Como medir | Status |
| --- | ---: | --- | --- |
| Feed reto seguro mm/min | confirmar | linha 500 mm em EPS barato | pendente |
| Feed curva seguro mm/min | confirmar | arco simples | pendente |
| Dry-run obrigatorio | true | regra de operador | pendente |
| Primeiro corte teste obrigatorio | true | regra de operador | pendente |
| Confirmacao do operador | true | checklist assinado | pendente |

## Compatibilidade LazyCam/Mach3

| Item | Valor | Como confirmar | Status |
| --- | --- | --- | --- |
| DXF R12 abre em escala 1:1 | confirmar | linha 500 mm no LazyCam | pendente |
| DXF 2007 abre corretamente | confirmar | teste comparativo | pendente |
| ARC real funciona | confirmar | arco simples no LazyCam | pendente |
| Polylines segmentadas funcionam | confirmar | arco segmentado | pendente |
| Layers sao preservadas | confirmar | abrir DXF com camadas | pendente |
| Extensao G-code aceita | confirmar | arquivo real `.tap`, `.nc` ou `.txt` | pendente |

## Golden samples obrigatorios

Guardar em `samples/real_machine/`:

```text
001_linha_500/
  original.dwg
  exportado.dxf
  lazycam_project.lcam
  mach3_gcode.tap
  foto_resultado.jpg
  medida_real.json

002_quadrado_100/
003_grade_5x5/
004_arco_simples/
```
