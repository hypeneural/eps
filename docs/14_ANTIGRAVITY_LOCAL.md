# Antigravity 2.35.0 — primeira entrega local
Documentacao consultada 2026-11-24: https://antigravity.google/docs/skills/ ; https://antigravity.google/docs/rules/ ; https://antigravity.google/docs/subagents ; https://antigravity.google/docs/customization-discovery/ .
AGENTS.md sem frontmatter e regra permanente. Skills em .agents/skills/<nome>/SKILL.md com name/description; regra modular usa trigger model_decision. Agente custom em .agents/agents/eps-engineer/agent.md. Preserve .codex. Confirme descoberta no menu Customizations ou abra novo chat; nao foi testado na instalacao 2.35.0.
## Terminal Windows
git status --short
git fetch origin
git switch feat/tp40-3d-industrial-package
git pull --ff-only
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
.venv/Scripts/python.exe scripts/first_test.py --output outputs/primeiro_teste

Abra summary.json, PDFs, PNGs e GLBs. Em cada subpasta execute scripts/verify_package.py. DXF calibracao_500mm e apenas teste de escala em LazyCam/Mach3 com fio desligado e operador. Nenhum DXF nos dois TP40 nominais.
## Render qualidade
Instale Blender 4.2+ por fonte oficial se necessario e autorizado. Exemplo:
python scripts/render_quality.py --blender "C:/Program Files/Blender Foundation/Blender 4.5/blender.exe" --input outputs/primeiro_teste/tp40_980_sks/24_eps_core.glb --output outputs/primeiro_teste/render_980_cycles.png
Repita com 23_assembly_reference.glb. Abra imagens; Cycles e opcional, nao modifica ZIP nem DXF.
## Bibliotecas
Shapely: poligonos/area/intersecao; Trimesh + Earcut: extrusao, volume e malha; GLB em m, STL mm; Pillow/NumPy: textura e normal; ezdxf: leitura independente R12. Referencias https://trimesh.org/trimesh.creation.html , https://trimesh.org/trimesh.visual.material.html , https://ezdxf.readthedocs.io/ , https://docs.blender.org/manual/en/latest/advanced/command_line/render.html .
## Limites
Nao afirmar fotorealismo sem inspecao. Nao confirmar medidas catalogo. Microdobras/fase/bordas, kerf, lead-in/out e perfil real pendentes. Nao alterar Mach3. Gere log de testes, versoes pip freeze, caminhos e status no relatorio local.

## Corpo de prova sintetico
primeiro_teste/trapezio_sintetico_400mm: DXF R12 aberto de 9 linhas, largura 400 mm, altura 40 mm, para teste de importacao/escala com fio desligado. As medidas sao de geometria matematica criada para calibracao, nao do fornecedor nem da telha fotografada. Nao e peca de encaixe, nao liberar producao. Parametros fisicos seguem confirmar.
