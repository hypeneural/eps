---
name: eps-first-test
description: Gera primeiro pacote de teste EPS SCARA, catalogos TP40, DXF de calibracao, malhas STL GLB e previews.
---
# Primeiro teste
Leia AGENTS.md e docs/14_ANTIGRAVITY_LOCAL.md. Confira branch, venv, pip check e unittest. Execute python scripts/first_test.py --help e gere em outputs/primeiro_teste. Abra imagens e PDF. Valide os hashes com scripts/verify_package.py. DXF de calibracao separado; TP40 nominal sem DXF. Use eps-render-quality se houver Blender. Reporte caminhos e bloqueios.

O segundo DXF e corpo de prova sintetico 400 x 40 mm, 9 LINE, somente importacao e dry-run sem aquecimento. Nao confundir com TP40 comercial.

No PC moderno Windows execute scripts/prepare_development.ps1 para reunir calibracoes e revisao TP40 em uma pasta versionada por data. Leia docs/16_DEVELOPMENT_HANDOFF.md. Nunca rodar bootstrap na maquina da fabrica.
