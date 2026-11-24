# Validacao Oficial e Melhorias Necessarias

Data: 2026-05-29

## Veredito

O repositorio deve ser hotwire-first: a maquina real e a SCARA CNC de fio quente/linha quente com DXF via LazyCam e execucao no Mach3/EPS.

Router/fresa nao representa o fluxo atual e foi arquivado em `archive/router_spindle_eps/`. O Codex nao deve usar fresa, spindle, RPM, Z seguro, profundidade por passe ou pocket 2.5D para projetos da SCARA.

## Fontes oficiais consultadas

| Fonte | Evidencia tecnica | Impacto |
| --- | --- | --- |
| [MachSupport - Mach3](https://www.machsupport.com/software/mach3/) | Mach3 transforma um PC em controlador CNC e processa G-code para controlar motores. | O repositorio deve respeitar Mach3/EPS como controlador final. |
| [MachSupport - LazyCam](https://www.machsupport.com/software/mach-3-add-ons-for-mill/) | LazyCam importa DXF/CMX para gerar G-code para Mach3, mas e beta. | DXF + checklist + teste real sao obrigatorios; nao confiar cegamente no LazyCam. |
| [Autodesk - DXF R12 Reference](https://damassets.autodesk.net/content/dam/autodesk/www/developer-network/platform-technologies/autocad-dxf-archive/acad_r12_dxf.pdf) | DXF R12 tem estrutura por group codes, entidades e layers. | Implementar allowlist/denylist de entidades e validador DXF. |
| [ezdxf r12writer](https://ezdxf.readthedocs.io/en/stable/addons/r12writer.html) | `r12writer` cria DXF R12 simples. | Usar `ezdxf` quando instalado e manter fallback textual controlado. |
| [OpenAI - AGENTS.md](https://developers.openai.com/codex/guides/agents-md) | `AGENTS.md` orienta o Codex no repositorio. | Instrucoes curtas, especificas e hotwire-first. |
| [OpenAI - Skills](https://developers.openai.com/codex/skills) | Skills empacotam instrucoes, referencias e scripts. | Skill deve carregar referencias sob demanda e focar SCARA. |
| [OpenAI - Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | Modelos podem aderir a JSON Schema. | `project_hotwire.schema.json` e contrato obrigatorio do Codex. |
| [OpenCV - Contours](https://docs.opencv.org/4.x/d4/d73/tutorial_py_contours_begin.html) | Contornos dependem de imagem binaria apos threshold/Canny. | Foto vira rascunho bloqueado, nao geometria final. |
| [Adobe - PDF Reference 1.7](https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.7old.pdf) | PDF e composto por objetos, stream de conteudo, texto e operadores graficos. | Gerar PDF tecnico simples, deterministico e sem dependencia pesada para ordem do operador. |

## Melhorias aplicadas

1. `scara_hotwire_eps` virou o unico processo ativo.
2. Router/fresa foi movido para `archive/router_spindle_eps/`.
3. `AGENTS.md`, README, skill e contratos agora bloqueiam conceitos de fresa no fluxo SCARA.
4. `project_hotwire.schema.json` passou a exigir `process.hotwire.wire_mode`.
5. Testes passaram a garantir que projeto SCARA com `tool`, Z, RPM ou profundidade de passe falha no schema.
6. Manifest/PDF ativos mostram dados do fio quente, nao dados de router.
7. `geometry_validator.py` valida duplicidade, sobreposicao colinear, segmento curto e limites de estoque/area util.
8. `02_ordem_corte_eps.pdf` virou ordem tecnica com aviso de status, bloco EPS, parametros hotwire, preview cotado e checklist LazyCam/Mach3.

## Gaps ainda pendentes

| Item | Proximo passo |
| --- | --- |
| Inventario real da SCARA | Preencher area util, origem, eixos, quantidade de fios, perda do fio, velocidade e formatos aceitos. |
| Golden samples | Coletar DXF/G-code/fotos/medidas reais em `samples/real_machine/`. |
| Foto -> rascunho YAML | Implementar pipeline `vision/photo_trace_to_yaml.py` mantendo bloqueio de producao. |

## Decisoes tecnicas resultantes

- O MVP exporta DXF R12 e pacote de conferencia, nao G-code.
- LazyCam continua como ponte do fluxo real, mas todo arquivo deve ser testado antes de corte.
- O PC antigo da maquina deve ser preservado; antes de qualquer atualizacao, fazer backup do perfil XML, screensets, macros/brains e exemplos.
- FreeCAD/LibreCAD podem conferir geometria, mas a saida de corte vem do exportador Python.
- G-code futuro deve ser dialeto Mach3 validado com arquivos reais da maquina, nao G-code universal.
- Router/fresa fica arquivado e fora do caminho ativo do Codex.

## Proxima acao recomendada

Preencher o inventario real de `machine_profiles/scara_hotwire_eps.yaml`:

- area util X/Y/Z;
- politica de zero;
- direcao positiva dos eixos;
- quantidade de fios/linhas;
- modo do fio;
- perda efetiva do fio quente;
- velocidade segura;
- formato DXF que abre melhor no LazyCam;
- extensao G-code aceita pelo Mach3;
- 3 a 4 amostras reais em `samples/real_machine/`.
