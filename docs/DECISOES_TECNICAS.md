# Decisoes Tecnicas

## 2026-05-29

- Fonte da verdade: `project.yaml` + `machine_profiles/scara_hotwire_eps.yaml`.
- Processo ativo: `scara_hotwire_eps` / `hotwire_2d`.
- Router/fresa foi arquivado em `archive/router_spindle_eps/` e nao deve ser usado na SCARA atual.
- G-code direto fica experimental e bloqueado por padrao.
- Foto gera apenas rascunho ate escala e medidas reais confirmadas.
- DXF de corte nao deve conter texto, cotas, hatch, spline, bloco complexo ou entidades 3D.
- `confirmar`, `null` tecnico e `profile_locked=false` bloqueiam producao.
- Validadores ativos ficam separados por responsabilidade: schema, maquina, production gate e hotwire.
- `geometry_validator.py` roda depois da geracao de `CutPath[]` e bloqueia duplicidade, sobreposicao colinear, segmento curto, bbox fora do estoque e bbox fora da area util quando houver dados numericos.
- `machine_profiles/scara_hotwire_eps.yaml` tem schema proprio em `schemas/machine_profile_hotwire.schema.json`.
- Em `cam_ready`, `machine_tested` e `production_released`, parametros hotwire confirmados precisam ser numericos validos; strings livres como `lento` ou `rapido` nao podem liberar producao.
- Projeto SCARA com fresa, spindle, RPM, Z seguro, profundidade por passe ou pocket deve falhar no schema.
- PDF tecnico e ordem de corte do operador. Deve incluir alerta de status, bloco EPS, modo do fio, quantidade de fios, perda/kerf, lead-in/out, feed, origem, bbox, preview vetorial cotado e checklist LazyCam/Mach3.
- Pacotes de saida geram `01_preview.png` para visualizacao direta no Codex app e `01_preview.svg` para preview vetorial.
- A entrega visual no Codex deve usar Markdown com caminho absoluto para `outputs/<project_id>/01_preview.png`.
- Antes de regenerar um pacote, o exportador remove apenas nomes de arquivos gerados conhecidos para evitar DXF antigo sobrando quando um projeto volta para `draft`.

## 2026-11-24

- Repositorio publicado em `https://github.com/hypeneural/eps` (branch `main`); `outputs/` permanece no `.gitignore`.
- Dependencias em `requirements.txt` (`PyYAML`, `jsonschema`, `ezdxf`). `ezdxf` e o escritor preferido do DXF R12.
- Escritor DXF reserva (sem `ezdxf`) gera estrutura R12 completa: HEADER `$ACADVER=AC1009`, TABLES (LTYPE, LAYER), ENTITIES, EOF.
- Exportador DXF suporta `LINE`, `ARC` e `CIRCLE` (`PathSegment.center`/`ccw`). Tipo de segmento nao suportado levanta erro; nunca e descartado em silencio.
- `validate_dxf` inspeciona por secao: ENTITIES para entidades de corte; BLOCKS aceita apenas `$Model_Space`/`$Paper_Space` (R12) e `*Model_Space`/`*Paper_Space`; bloco de usuario e entidade proibida em BLOCKS falham.
- Novo warning `geometry_machine_area_unverified` quando `work_area` X/Y e `confirmar` e o status gera DXF; antes a checagem de area util era pulada sem aviso.
- Novo template `tp40_core` (miolo EPS de telha TP40): topo do miolo = topo do bloco; linha de corte ondulada simetrica (`4*n_waves + 1` segmentos `LINE`); parametros numericos obrigatorios; gate `tp40_profile_not_confirmed` (warning em `draft`, erro em `validated_geometry` ou superior); compensacao do fio opcional por offset miter de `effective_kerf_mm / 2`; linhas de referencia (bloco, linha nominal) aparecem em preview/PDF/SVG e nunca no DXF. Exemplo `007_tp40_nucleo_eps.yaml` usa medidas **nominais** e fica em `draft`.
- `CutJobResult.reference_segments` e `view_bbox` adicionados para preview/PDF; `bbox` continua sendo so a geometria de corte.
- Manifest ganha `template` e `tp40`; PDF ganha secao "Perfil TP40" e alerta "MEDIDAS TP40 NOMINAIS" enquanto nao confirmado.
- Producao continua bloqueada ate o inventario real da SCARA (ver `docs/12_AUDITORIA_E_PRONTIDAO.md`).

## Pacote 3D TP40
- Poligonos nominais fechados para EPS, contraforma e chapa negativa simplificada; percurso do fio separado.
- STL em mm, GLB em metros, textura sintetica EPS, preview CPU. Sem malha 3D como arquivo CAM.
- Catalogos nao homologados; microdobras/fase/bordas precisam de confirmacao.
- DXF do contorno fechado de conferencia bloqueado.

## Entrega e agente Antigravity
- AGENTS.md e skills .agents/skills; .codex preservado. Agente especializado em .agents/agents/eps-engineer/agent.md.
- Primeiro teste gera calibracao e TP40 nominais separados. Confirmacao fisica nunca automatizada.
- ZIP validado por lista de manifest e SHA256, reabertura DXF por ezdxf. Staging antes de publicacao.
- GLB com normal map sintetico. Blender Cycles opcional e separado dos arquivos com hash; preview CPU permanece padrao.

- Corpo de prova sintetico separado para teste de importacao: 400 x 40 mm, 9 LINE, nenhum parametro fisico assumido.
- Perfil por pontos invalido nao gera quadrado silencioso; gates de producao exigem confirmacao explicita e capacidades numericas.

## Homologacao local PC de desenvolvimento (2026-11-24)
- `scripts/render_quality.py` e `scripts/blender/render_eps.py` expandidos com `--view` para 6 vistas studio Cycles (`perspective`, `section_front`, `microgroove_detail`, `assembly`, `exploded`, `texture_closeup`), material procedural de EPS branco com perolas fundidas arredondadas (`1 - d^2` + seams suaves), chapa Galvalume metalica spangle, color management `AgX` e deteccao automatica OptiX/CUDA com fallback CPU.
- `scripts/prepare_tp40.py` gera automaticamente as 6 vistas Cycles (`30..35_*_cycles.png`) quando Blender e localizado (`--blender auto`) e preserva a separacao estrita sem DXF/TAP.
- `src/epscad/visual/review_drawing.py` passou a incluir detalhe ampliado do modulo (196 mm) destacando a microdobra central (48 x 2 mm) e tabela resumo das cotas nominais em `29_section_review.png`.
- `.agents/agents/eps-engineer/agent.md` vinculado explicitamente as 5 skills locais.
- Testes de regressao adicionados para invariancia do perfil sob variacao de espessura minima, preservacao das 5 microdobras e contrato CLI das 6 vistas Cycles (`tests/test_render_quality.py`, `tests/test_roof_review.py`).

## Arquitetura do agente (24/11/2026)
AGENTS.md curto, skills sob demanda, agentes separados e preflight no CI; checkpoint local ignorado. Workflows legados não adicionados; /run-workflow para auditoria ampla com aprovação. Ver docs/18_GUIA_AGENTE.md e docs/19_WORKFLOWS_AGENTE.md.
