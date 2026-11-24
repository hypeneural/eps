# Guia operacional do agente EPS
Estado e comandos devem ser confirmados no checkout atual; relatórios antigos são evidências históricas, não fonte de status atual.
## Roteamento (uma rota inicial)
| Intenção | Skill | Entrada principal |
| --- | --- | --- |
| Instalar, primeiro teste, regressão | eps-first-test | scripts/first_test.py |
| TP40 base lisa, espessura, CAD | eps-tp40-engineering | scripts/prepare_tp40.py |
| TP40 comercial simplificada | eps-tp40-engineering | scripts/new_tp40.py |
| ZIP/DXF/TAP histórico | eps-historical-review | scripts/review_historical_roof.py |
| Render, textura, microdobra | eps-render-quality | scripts/render_quality.py |
| Conferir pacote e DXF | eps-package-audit | scripts/verify_package.py |
| Auditoria de código, PR | eps-audit | scripts/agent_preflight.py |
| Retomar sessão | eps-resume | scripts/agent_preflight.py |
| Galeria, quando presente | eps-publish-model | scripts/build_gallery.py |
Portal só existe no checkout que contém portal/ e docs/17_PORTAL_ISONUNES.md. Se ausente, não inventar arquivo; usar worktree da branch feat/isonunes-production-gallery. Agentes especializados: eps-engineer (CAD), eps-reviewer (verificação), eps-portal quando presente. Main coordena e integra.
## Ordem de autoridade
AGENTS.md e gates executáveis -> schemas/catalogos/perfil e código atual -> docs técnicas atuais -> relatórios históricos -> referências externas. Em divergência, não alterar segurança; documentar achado e verificar fonte real. O relatório 17_HOMOLOGACAO_LOCAL_RELATORIO.md valida a referência TP40 histórica, não o encaixe físico. Nunca usar preview de docs como prova de pacote atual.
## Checkpoint local
Crie .eps-agent/checkpoint.json apenas para tarefas longas, em cada worktree, sem segredos nem dados da fábrica. Formato sugerido:
```json
{"task":"objetivo","branch":"branch","head":"SHA verificado","skill":"eps-tp40-engineering","phase":"validate","completed":[{"command":"comando","exit_code":0,"evidence":"caminho local"}],"artifacts":["caminho local"],"blockers":[],"next":"próxima ação"}
```
Atualize após etapa relevante. Antes de retomar confira Git, arquivos e hashes; checkpoint não é fonte de autorização. Não comitar nem carregar logs completos desnecessariamente.
## Validação incremental
Preflight -> teste focal -> pip check + suíte completa para mudanças -> validação de artefatos -> revisão independente quando risco alto -> CI no commit -> inspeção visual/HTTPS/operador quando aplicável. Não rodar Blender para corrigir CSS se houver pacote íntegro. Não instalar novamente dependências que já passaram pip check. Não usar agentes paralelos para editar os mesmos arquivos.
## Definição de pronto
Comando e exit code reais, branch/commit, arquivos, estado de validação, hashes quando aplicáveis, inspeção real ou limitação explícita, próximos passos. Separar: CAD nominal, render, portal local, portal HTTPS e homologação física. Publicação exige autorização separada.
