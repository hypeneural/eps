---
name: eps-audit
description: Audita mudanças, regressões, documentação, contratos, desempenho e riscos nas branches EPS; use em PR, bug ou homologação técnica.
---

# Auditoria
Leia docs/18_GUIA_AGENTE.md e compare diff com base explícita, não com main indiscriminadamente. Identifique arquivos alterados e contratos afetados. Para revisão ampla, consulte docs/19_WORKFLOWS_AGENTE.md. Classifique achados P0/P1/P2 com arquivo, linha, evidência, impacto, correção e teste. Prefira revisores independentes, sem edição concorrente. Ao corrigir, um integrador aplica mudanças, roda teste focal e suíte. Não alterar gates para resolver falhas. Separe fatos observados de hipóteses e reporte verificação não realizada.
