# Antigravity — início rápido local
App 2.35.0 conforme relatório de homologação. Para customizações e documentação oficial veja docs/19_WORKFLOWS_AGENTE.md; para roteamento e retomada veja docs/18_GUIA_AGENTE.md.
Abra a raiz do worktree correspondente; não use o PC Windows 7 da fábrica.
```powershell
git status --short
git branch --show-current
git rev-parse HEAD
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/agent_preflight.py
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
```
Reutilize a venv se íntegra. Para bootstrap completo veja docs/16_DEVELOPMENT_HANDOFF.md. Para TP40 base lisa use prepare_tp40.py, não new_tp40.py. Veja docs/17_HOMOLOGACAO_LOCAL_RELATORIO.md para resultados observados (62 testes no commit histórico, seis vistas Cycles); não reaproveitar contagem como resultado atual.
## Render
`python scripts/render_quality.py --help` lista vistas e opções. `python scripts/prepare_tp40.py --blender auto --output outputs/tp40_review_nova` gera pacote completo; renders isolados ficam fora do ZIP já verificado. Não instalar Blender na fábrica. Inspecionar imagens reais.
## Calibração e pendências
500 mm e trapézio sintético 400 × 40 mm são somente importação/dry-run sem calor supervisionado. Microdobras da referência normalizada já recuperadas; bordas e encaixe real, kerf, origem, fios, limites, velocidade, aquecimento e configuração ativa continuam pendentes. Ver inventário.
