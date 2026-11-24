---
name: eps-first-test
description: Prepara o ambiente de desenvolvimento e gera calibrações SCARA e primeiro pacote nominal TP40; use em instalação, smoke test ou regressão integral.
---

# Primeiro teste
Leia docs/16_DEVELOPMENT_HANDOFF.md. Confirme PC moderno, branch e venv. Execute pip check e unittest. Use scripts/first_test.py --help e escolha pasta nova em outputs/. Para fluxo completo Windows use scripts/prepare_development.ps1 (Blender opcional). Valide os ZIPs de calibração e os modelos de revisão; linha 500 mm e trapézio sintético 400 × 40 mm são testes, não peças comerciais. Use eps-package-audit e eps-render-quality apenas quando necessário. Se outputs anteriores íntegros existem, reutilize-os; não reinstale ou renderize sem motivo. Entregue caminhos, exit codes e pendências.
