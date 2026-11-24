---
name: eps-resume
description: Retoma uma tarefa EPS interrompida, após troca de conversa, compactação de contexto ou trabalho de outro agente, sem repetir ações verificadas.
---

# Retomar
Leia docs/18_GUIA_AGENTE.md. Confira branch, HEAD e status Git; leia .eps-agent/checkpoint.json se disponível no worktree. Compare escopo, commit e caminhos com o estado real. Verifique apenas os artefatos relevantes antes de reutilizá-los. Se checkpoint estiver ausente ou desatualizado, reconstrua estado por git diff/log, relatório e manifests, sem assumir sucesso. Nunca restaurar autorização de deploy ou produção de um checkpoint. Selecione skill atual, complete o próximo passo e atualize checkpoint local. Não comitar checkpoint.
