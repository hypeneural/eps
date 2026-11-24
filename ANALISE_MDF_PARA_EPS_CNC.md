# Analise MDF para EPS CNC

Data: 2026-05-29

Este documento registra a adaptacao da arquitetura MDF para o projeto EPS atual. A decisao vigente e hotwire-first: a maquina ativa e uma SCARA CNC de fio quente/linha quente com fluxo DXF -> LazyCam -> Mach3/EPS.

## O que reaproveitar do MDFCAD

| MDFCAD | EPS SCARA hotwire |
| --- | --- |
| YAML/JSON como fonte da verdade. | `project.yaml` + `machine_profiles/scara_hotwire_eps.yaml`. |
| Templates deterministicas. | `straight_cut`, `square_test`, `grid_blocks`, `profile_2d`, `photo_trace`. |
| Validador antes de exportar. | Schema, production gate, hotwire, DXF e geometria. |
| PDF/manifest de producao. | Ordem de corte EPS, manifest tecnico e checklist LazyCam/Mach3. |
| Foto como referencia. | Foto fica bloqueada ate escala e medidas confirmadas. |

## O que muda em EPS/fio quente

- O centro do projeto nao e lista de chapas/pecas, e sim `CutPath[]`.
- A compensacao vem da perda termica do fio, nao de serra ou fresa.
- O fluxo real usa DXF antigo, LazyCam e Mach3/EPS.
- O DXF final nao deve conter texto, cotas, hatch, splines, blocos complexos ou entidades 3D.
- G-code direto fica experimental ate existirem golden samples reais.

## Dados reais que ainda precisam ser medidos

- area util X/Y/Z;
- origem e politica de zero;
- direcao positiva dos eixos;
- quantidade de fios/linhas;
- modo do fio;
- perda efetiva do fio;
- velocidade segura;
- formato DXF que abre melhor no LazyCam;
- extensao G-code aceita pelo Mach3;
- exemplos reais em `samples/real_machine/`.

## Regra para o Codex

Codex interpreta pedidos e edita YAML/codigo. Python calcula e valida. Exportadores escrevem DXF/PDF/SVG/manifest. Operador confere e faz dry-run.
