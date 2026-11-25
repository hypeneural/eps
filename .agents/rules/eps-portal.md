---
trigger: model_decision
description: Aplica a portal Iso Nunes, templates, frontend, catálogo, publicação, downloads, FTPS ou HTTPS.
---
Use eps-publish-model. Site público sem login não é confidencial; arquivos TAP de conferência só podem ir online na área privada autenticada (`/conferencia/`, HTTP Basic Auth `401`/`200`), separados da apresentação comercial (`publico.html`) e da produção homologada (`check_mach3_delivery.py`). Preserve allowlist, hashes, revisão, acesso a download sem JS e visualização 3D opcional. Deploy não faz parte de teste/CI; requer autorização explícita e credenciais locais protegidas fora do Git.
