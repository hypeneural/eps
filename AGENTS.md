# EPS CutPlan — Antigravity e Codex

## Missao
Gerar perfis EPS em mm com YAML, catalogo rastreavel e perfil SCARA. Python calcula e exporta; agente interpreta e executa scripts. Fluxo DXF R12 -> LazyCam -> Mach3/EPS. STL/GLB sao visualizacao.

## Regras permanentes
- Nunca inventar medidas, fabricante, origem, eixos, velocidade, perda termica, quantidade de fios ou confirmacoes.
- Catalogo/foto: draft sem DXF. validated_geometry: somente teste com medidas confirmadas. cam_ready e superiores exigem perfil real travado. G-code direto desabilitado.
- Separar poligono nominal, compensacao termica, trajeto do fio e referencias. Nao exportar chapa ou contorno visual para corte.
- SCARA hotwire_2d; sem spindle, RPM, fresa ou router. Nao alterar PC/controlador da maquina.
- Preservar alteracoes locais. Nao marcar flags de confirmacao para satisfazer testes.
- Toda mudanca dimensional exige nova conferencia humana.

## Procedimento
1. Ler docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md, docs/13_TP40_3D_REMOTE.md e docs/14_ANTIGRAVITY_LOCAL.md.
2. Usar skills em .agents/skills ou .codex/skills conforme plataforma. Executar scripts com --help.
3. Usar venv Python 3.11 ou 3.13; pip check e unittest.
4. Gerar primeiro teste via scripts/first_test.py. Abrir renders, PDF e modelos 3D reais; verificar hashes e relatorios.
5. Se Blender disponivel, usar scripts/render_quality.py para PNG Cycles separado; nao declarar render executado sem inspecao.
6. Entregar caminhos absolutos, status, testes e dados fisicos pendentes. Atualizar docs e regressao numerica em mudanca de codigo.

## Contratos
schemas/project_hotwire.schema.json e machine_profile_hotwire.schema.json. DXF R12 2D sem texto/cotas, spline, blocos de usuario ou entidades 3D. STL em mm, GLB em m. Dry-run sem aquecimento, escala 1:1, origem, entrada/saida e teste supervisionado obrigatorios antes de corte.

## Evidencia historica
Nao enviar ZIPs originais, XML, PST, macros ou desenhos industriais de terceiros ao GitHub publico. Use private_evidence/ e local_catalogs/. A geometria CAD historica pode conter sobreposicoes e trajetorias auxiliares; nunca extrudar todo o DXF como peca. Use scripts/review_historical_roof.py com limites explicitamente conferidos para revisao visual. Nao gerar arquivo de maquina desse fluxo. Leia docs/15_HISTORICAL_EVIDENCE.md.
