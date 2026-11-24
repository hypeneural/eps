---
name: eps-publish-model
description: Gera e publica galeria Iso Nunes com imagens e GLB sob demanda, revisão, ZIP e DXF somente homologado.
---
Leia docs/17_PORTAL_ISONUNES.md. Use scripts/build_gallery.py com registro local. Nunca copie ZIP original ou dados privados. Valide public_authorized e status, hash de DXF aprovado, revisão e ZIP sanitizado. Gere primeiro snapshot local, abra páginas e valide 800x600/1024x768/celular e JS desligado. Deploy FTPS apenas com autorização explícita, senha por ambiente e --execute; não exponha credenciais. Não publique DXF de teste nem G-code. Revogação retira arquivos anteriores do servidor, não cópias baixadas.
