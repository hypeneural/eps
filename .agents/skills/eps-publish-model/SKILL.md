---
name: eps-publish-model
description: Gera, revisa e prepara publicação da galeria Iso Nunes; use para UX, busca, imagens, modelo 3D, revisão, download e FTPS.
---

# Rota
Leia docs/17_PORTAL_ISONUNES.md. Confirme worktree portal. Se tarefa for UI, use pacote TP40 já verificado ou gallery_demo.py; não repetir Blender sem motivo. Para cadastrar modelo, register_gallery_model.py --help; autorização pública explícita e revisão crescente. build_gallery.py --help em pasta nova. Logo oficial via fetch_portal_logo.py; wordmark provisório não é logo oficial.
# Validação
Execute testes de publishing e check_gallery_browser.py quando Playwright instalado (800x600, 1024x600/768, 1366x768, 390 e 320, sem JS). Inspecione imagens, busca, filtros, ZIP, navegação, 3D carregado só por clique; teste EPS e montagem separadamente. Reutilize renders verificados. Sem dados privados nem DXF de teste. Produção exige status, gate revalidado e aprovação por hash.
# Publicação
Deploy local dry-run primeiro. --execute somente com autorização explícita atual, FTPS TLS e raiz confirmada; senha fora do Git. --allow-production adicional para corte homologado. Após deploy, check_gallery_live.py --help com snapshot exato e teste navegador real; retirada não revoga cópias baixadas. Se não houver autorização ou conexão, entregue snapshot, relatório e bloqueio, sem afirmar site no ar.
