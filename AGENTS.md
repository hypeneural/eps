# EPS CutPlan — instruções permanentes
## Antes de executar
- Abra a raiz do worktree correto. Confira `git status --short`, `git branch --show-current`, `git rev-parse HEAD`. Preserve alterações alheias. Não troque branch, faça merge, reset ou push destrutivo automaticamente.
- Leia README.md e consulte docs/18_GUIA_AGENTE.md para escolher UMA rota inicial. Execute `python scripts/agent_preflight.py` (na venv se existir). Não leia todo o repositório por padrão.
- Use a skill da tarefa; leia contratos e código adicionais somente quando necessário. Execute scripts existentes com --help antes de inventar novas interfaces.
- Retome pelo checkpoint local se existir e conferir branch, commit e artefatos; não repetir trabalho validado sem motivo.
## Invariantes
- PC de desenvolvimento moderno != PC controlador Windows 7 da fábrica. Não instalar, conectar, comandar ou alterar Mach3/SCARA remotamente.
- CAD em mm, STL em mm, GLB em m; SCARA hotwire_2d, DXF R12 -> LazyCam Foam -> Mach3. Geometria nominal, chapa, contraforma, estoque e trajetória são distintos. G-code direto faz parte da rota Mach3 dedicada; geração local para desenvolvimento, simulação e teste supervisionado é permitida. A rota DXF legada permanece separada.
- Foto/catálogo/histórico não homologam peça física. draft sem DXF; validated_geometry somente teste; demais status sujeitos aos gates. Nunca inventar medidas, kerf, velocidade, potência, origem, fios, eixos ou confirmações. Não mudar flags para passar testes. F600/S300 históricos não são parâmetros autorizados.
- TP40 base lisa com microdobra: scripts/prepare_tp40.py e tp40_980_microgroove_review.yaml. Não substituir por new_tp40.py (referências comerciais simplificadas).
- Nunca publicar evidências da fábrica, credenciais, macros, XML/PST, outputs integrais ou dados privados. private_evidence/, local_catalogs/, portal_local/, .eps-agent/, .venv/ e outputs/ são locais. Verifique staged diff antes de commit.
- Portal, quando presente: publicação web != autorização de fabricação. Somente TAP/DXF de produção revalidado e aprovado por hash no catálogo público. Candidatos de teste ficam locais, sem exigir aprovação comercial prévia. FTPS somente com autorização explícita; não revelar segredos.
## Execução e término
1. Declare objetivo, branch, skill e critérios verificáveis. Para tarefa complexa, use checkpoint conforme docs/18_GUIA_AGENTE.md.
2. Execute a menor mudança coerente; testes focados primeiro, depois pip check e suíte completa quando houver alteração de código. Não desative testes/gates. Não instale dependência sem justificar.
3. Valide artefatos, hashes e unidades; abra imagens/GLB se a tarefa envolver visualização. Distinguir teste executado, inspeção visual, CI, HTTPS e homologação física.
4. Reporte comandos/exit codes, arquivos, commit, limitações e próximo passo. Não confundir arquivo gerado, teste offline, teste presencial e liberação comercial.

## Rota Mach3 direto (branch dedicada)
Leia docs/27_MACH3_TESTE_ANTES_DA_LIBERACAO.md. O agente deve gerar e testar software, simular trajetórias e preparar candidatos locais sem depender de liberação comercial prévia. Use scripts/prepare_mach3_trial.py para teste supervisionado com parâmetros reais revisados e autorização de teste, sem mudar profile_locked ou production_confirmed. Use arquivos históricos apenas com identidade e proveniência explícitas; nunca substitua um modelo por outro. Não invente limites, parâmetros térmicos ou confirmações. Não publique candidato como produção nem opere a máquina. Após teste físico, use a rota de aprovação por hashes existente.
