# Workflows Antigravity — execução e revisão
Documentação oficial consultada em 24/11/2026 (App 2.35.0, changelog de 23/11):
- https://antigravity.google/docs/changelog?tab=hub
- https://antigravity.google/docs/customization-discovery/
- https://antigravity.google/docs/rules/
- https://antigravity.google/docs/skills/
- https://antigravity.google/docs/subagents
- https://antigravity.google/docs/migration/workflows-to-skills/
- https://antigravity.google/docs/dynamic-workflows/
- https://antigravity.google/docs/commands/learn/
## Decisões
AGENTS.md raiz sem frontmatter; rules com trigger válido; skills em .agents/skills/<nome>/SKILL.md; agentes em .agents/agents/<nome>/agent.md. Não criar workflows Markdown legados. Procedimentos estáticos são skills; Dynamic Workflows são scripts gerados/revisados no runtime do Antigravity. Não confundir com GitHub Actions. Não adicionar hooks que executam shell automaticamente nem ampliar permissões. Verifique ferramentas na instalação antes de alterar allowlists. Skills são descobertas por descrição; não vincular todas antecipadamente.
## Quando usar /run-workflow
Auditoria de PR amplo, verificação de CAD/render/portal independentes. Para alteração pequena, uma skill e um executor bastam. Use 2–3 revisores com escopo somente leitura, sem deploy, sem acessar a fábrica. Um integrador aplica correções em sequência. Se precisar editar em paralelo, workspace branch isolado e arquivos disjuntos; revisar diffs antes de integrar. Aprovar o script mostrado pela App, sem autorização genérica.
Prompt sugerido (não é script obrigatório):
> /run-workflow Descubra branch, diff e contratos. Em paralelo audite CAD/gates, render/artefatos e portal/segurança se presentes, sem editar. Cada agente retorna achados com prioridade, arquivo:linha, evidência, correção e teste. Consolide sem duplicatas. Um integrador corrige somente o escopo autorizado, roda testes focais e suíte. Um revisor confirma as correções. Nenhum deploy, operação CNC ou merge automático.
## Descoberta e aprendizado
Abra raiz de cada worktree, Customizations > Installed e Settings > Projects > Customizations; confira skills/agentes. No CLI /skills reload quando disponível; no App abra conversa nova se necessário. Não assumir que regras em subpastas são carregadas automaticamente. Use /learn para propor melhoria específica e revisar diff, não para registrar credenciais, paths privados ou alterar gates. /btw pode esclarecer uma dúvida sem interromper a tarefa principal; não é necessário para execução.
## GitHub Actions
CI valida configuração local, dependências, testes e exemplos; portal tem workflow Playwright separado quando presente. CI não instala Blender, não faz deploy e não comanda a CNC. A execução do Antigravity real, GPU e hospedagem precisam de validação local/HTTPS.
