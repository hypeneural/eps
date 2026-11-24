---
name: eps-publish-model
description: Gera, revisa e prepara publicação da galeria Iso Nunes; use para UX, busca, imagens, modelo 3D, revisão, download e FTPS.
---

# Fluxo por solicitação em linguagem natural
Para pedidos como *"Gere uma TP40 base lisa de 1 metro, espessura mínima de 31 mm, renderize, valide e publique para conferência na galeria Iso Nunes"*:
1. Identifique o catálogo correto com `python scripts/generate_catalog.py --list` (`tp40_980_microgroove_review` para TP40 base lisa; nunca confundir com `tp40_980_sks`/`tp40_1020_isoeste` simplificados).
2. Gere o pacote (ou reaproveite pacote já verificado sem renderizar de novo se não houve mudança CAD): `python scripts/generate_catalog.py tp40_980_microgroove_review --length 1000 --thickness 31 --output <pasta_nova> --blender auto`.
3. Inspecione os renders reais, `review.json`, `SHA256SUMS.txt` e integridade do ZIP de revisão (zero arquivos `.dxf`/`.tap`).
4. No worktree do portal (`feat/isonunes-production-gallery`), baixe a logo oficial (`scripts/fetch_portal_logo.py`) e opcionalmente o visualizador 3D local fixado com licença Apache-2.0 (`scripts/fetch_model_viewer.py`).
5. Cadastre a revisão com autorização pública explícita (`scripts/register_gallery_model.py add --id <slug> --revision rXX --name "<nome>" --category <cat> --source "<caminho_absoluto>" --public-authorized`) e gere o site em pasta nova (`scripts/build_gallery.py`).
6. Execute validação automatizada de navegador (`scripts/check_gallery_browser.py` nas 6 resoluções + sem JS), teste WebGL2/3D sob demanda e rode o dry-run de deploy (`scripts/deploy_gallery.py --site <pasta>`).
7. Nunca execute `--execute` sem autorização explícita de publicação, credencial rotacionada em variável de ambiente e raiz remota dedicada confirmada.

# Rota e validação
Leia `docs/17_PORTAL_ISONUNES.md`. Confirme worktree portal. Se tarefa for UI, use pacote TP40 já verificado ou `gallery_demo.py`; não repetir Blender sem motivo. Wordmark provisório não é logo oficial. Execute testes de publishing (`tests/test_publishing.py`) e `check_gallery_browser.py` (800×600, 1024×600/768, 1366×768, 390×844, 320×568 e sem JS). Inspecione imagens, busca, filtros, ZIP, navegação, 3D carregado só por clique (EPS e montagem). Sem dados privados nem DXF de teste. Produção exige status `production_released`, gate revalidado e aprovação por hash.

# Publicação
Deploy local dry-run primeiro. `--execute` somente com autorização explícita atual, FTPS TLS estrito (verificar hostname canônico do certificado TLS do servidor, ex.: `br46-pl.valueserver.net`) e raiz dedicada confirmada; senha fora do Git. `--allow-production` adicional para corte homologado. Após deploy, `scripts/check_gallery_live.py --site <pasta> --url https://eps.etijucas.com.br` e conferência no navegador real. Retirada não revoga cópias baixadas. Se não houver autorização ou conexão, entregue snapshot, relatório e bloqueio, sem afirmar site no ar.

## Portal V3
Leia docs/21_PORTAL_V3_AUDITORIA.md. Reutilize pacote e registro local. Gere snapshot novo, teste busca por medidas, download por hash e catálogo pequeno/grande. Use viewer local com SHA verificado, sem CDN. PNG técnico é conferência. Não use --initialize em site já publicado. Não liberar DXF para melhorar aparência. Verifique HTTPS após deploy autorizado.

Para produção já homologada, use scripts/check_release_candidate.py apenas para obter os três hashes; aprovação humana explícita no registro. Não invente confirmação nem marque approved:true automaticamente. Veja contrato V3.

## UX V4
Consulte docs/24_PORTAL_V4_UX.md. Teste foco modal, restauração de busca no mesmo separador, downloads individuais, retorno do 3D, contraste e reflow. Não misturar melhorias UX com liberação industrial. Sem deploy automático.

## Mach3 direto (branch experimental)
Leia docs/25_MACH3_DIRECT_TAP.md. TAP regenerado e aprovado por hashes é o download direto para CNC_V. DXF permanece alternativa de CAM. Não publicar candidato, teste ou histórico bruto. Não emitir TAP de draft. Revalidar perfil, parâmetros, limites, ordem e autorização, sem operar máquina. Teste apenas em ambiente local sem hardware.

Na branch Mach3, teste local não exige liberação comercial prévia. Use prepare_mach3_trial.py com parâmetros revisados e saída fora do site. Não coloque candidatos em ZIP público ou catálogo comercial. Ver docs/27_MACH3_TESTE_ANTES_DA_LIBERACAO.md.
