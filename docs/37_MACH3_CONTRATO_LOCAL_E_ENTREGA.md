# Mach3 — resolver vínculo do contrato e perfil privado
Base: 989135e. O erro de lote foi Contract is not bound to this profile. Um arquivo TEMPLATE não é configuração aprovada. O hash é calculável pelo software; medições e confirmação humana não são.
## Uma etapa de vínculo, sem edição manual de SHA-256
Depois que o responsável revisar os valores do snapshot e confirmar os campos do contrato de teste, executar no worktree Mach3 (arquivos locais, não versionados):
```powershell
python scripts/prepare_mach3_batch.py --profile portal_local/local_scara_snapshot.yaml --contract portal_local/local_trial_contract.reviewed.json --bind-reviewed-contract portal_local/local_trial_contract.bound.json
python scripts/prepare_mach3_batch.py --handoff outputs/private_trial_handoff_5models --slab-library outputs/private_test_library_v6 --profile portal_local/local_scara_snapshot.yaml --contract portal_local/local_trial_contract.bound.json --approvals portal_local/approvals.json --output outputs/tap_lote_revisado
```
O primeiro comando somente calcula o hash do perfil; recusa confirmações falsas, valores ausentes e re-vinculação silenciosa de um contrato já ligado a perfil diferente. O segundo efetivamente gera os candidatos autorizados. Não reutilize saída anterior e não faça publicação industrial dos candidatos.
## Perfil real privado no fluxo comercial
O loader antes lia sempre o YAML versionado, inclusive após existir um snapshot de campo. Agora o responsável pode indicar explicitamente um perfil privado completo, com schema válido:
```powershell
$env:EPS_SCARA_PROFILE_FILE = (Resolve-Path 'portal_local/scara_hotwire_eps.yaml').Path
```
O mesmo loader é usado por build_job, validação, candidato e aprovação de publicação. Não modifica perfil padrão, não trava automaticamente o perfil e não marca production_allowed. O snapshot mínimo de teste não substitui perfil completo de produção. O perfil real deve corresponder à revisão testada; alterações invalidam hashes. Não versionar a configuração real. Não compartilhar a variável com testes sintéticos. Depois, Remove-Item Env:EPS_SCARA_PROFILE_FILE.
## Publicação e verificação
Gerar pacote da revisão real aprovada, conservar renders da peça correspondente, registrar require_tap:true e todos os hashes do candidato aprovado no registry local. Usar build_gallery, deploy_gallery --allow-production --execute e check_mach3_delivery --https com snapshot novo. A verificação HTTPS agora roda também quando o aceite industrial é parcial; não confundir integridade HTTP com aprovação física.
## Estado e separação da área privada de conferência
A disponibilização online dos 9 TAPs de conferência na área privada autenticada (`/conferencia/`, ver `docs/39_AREA_PRIVADA_CONFERENCIA_TAP.md`) é independente desta etapa comercial de fabricação. Não há dados novos de curso útil, kerf, origem e I/O ainda; catálogos e TAPs antigos não substituem medições. Não forçar flags nem marcar 9/9 no `check_mach3_delivery.py` enquanto não houver homologação física real.
