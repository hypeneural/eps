# Auditoria do repositorio e prontidao para corte

Data: 2026-11-24

## Veredito

| Pergunta | Resposta |
| --- | --- |
| Funciona? | **Sim.** Validacao, geracao de pacote, DXF R12 e testes passam (`python -m unittest discover -s tests -p "test_*.py"`). |
| Desenha pecas para teste de corte? | **Sim**: linha, quadrado, grade, perfil 2D por pontos e TP40 trapezoidal (`tp40_core`). DXF liberado a partir de `validated_geometry`. |
| Pronto para corte de producao? | **Nao, por design.** O perfil `scara_hotwire_eps` ainda tem campos `confirmar` e `profile_locked=false`. |

## O que falta para producao (so a maquina real resolve)

Preencher `machine_profiles/scara_hotwire_eps.yaml` a partir de `docs/02_INVENTARIO_MAQUINA_SCARA.md`:

- area util X/Y/Z, origem, politica de zero/home, sentido positivo de X/Y;
- quantidade de fios, perda efetiva do fio, segmento/raio minimos;
- feed reto e feed de curva seguros;
- teste de importacao do DXF R12 no LazyCam (escala 1:1, layers) e extensao do G-code do Mach3;
- golden samples em `samples/real_machine/`;
- backup do PC Mach3 antes de qualquer mudanca (`docs/08_BACKUP_PC_MACH3_PERFIL_EPS.md`).

Enquanto isso, qualquer projeto em `cam_ready` ou superior falha (`confirmar_blocks_production`, `profile_locked_required`).

## Achados da auditoria e correcoes aplicadas

| Achado | Correcao |
| --- | --- |
| Pasta sem git/remote | `git init`, push para `hypeneural/eps` (main). |
| `ezdxf` nao instalado: DXF saia por escritor reserva sem HEADER/TABLES/LAYER | `requirements.txt`; escritor reserva agora gera HEADER (`AC1009`), LTYPE, LAYER, ENTITIES, EOF. |
| `ARC`/`CIRCLE` descartados em silencio no DXF | Exportam de verdade (`PathSegment.center`, `ccw`); tipo nao suportado levanta `ValueError`. |
| Validador de DXF lia o arquivo inteiro e confundia o `BLOCKS` padrao do R12 com bloco proibido | Valida por secao; aceita `$Model_Space`/`$Paper_Space`; rejeita blocos de usuario; bbox inclui ARC/CIRCLE/POLYLINE. |
| Area util da maquina `confirmar` pulava a checagem de bbox sem avisar | Novo warning `geometry_machine_area_unverified` em `validated_geometry` ou superior. |
| Sem template de perfil de telha | `tp40_core` (ver `docs/11_TP40_TRAPEZOIDAL.md`). |
| Docs desatualizados (contagem de testes, passos) | README, IMPLEMENTACAO e DECISOES_TECNICAS atualizados. |
| Sem CI | `.github/workflows/ci.yml` (Windows + Ubuntu). |

## Limitacoes conhecidas (nao bloqueiam teste, registradas)

- Compensacao do fio (kerf) so existe no `tp40_core`; os demais templates usam `centerline`.
- Lead-in/lead-out nao viram geometria (ficam no LazyCam).
- `photo_trace` continua sem geometria (apenas rascunho).
- Validadores de geometria tratam segmentos pelo comprimento da corda; nenhum template atual gera ARC.
- O PDF e escrito por gerador proprio (sem reportlab); conteudo e simples e de uma pagina.

## Checks executados

```text
python -m unittest discover -s tests -p "test_*.py"   -> 46 testes OK
generate_project 007_tp40_nucleo_eps (draft)           -> preview/PDF/manifest, sem DXF
TP40 com perfil confirmado (pasta temporaria)          -> DXF AC1009, 21 LINE, bbox 1000 x 40 mm, validate_dxf ok
ezdxf.readfile no DXF gerado                           -> AC1009, somente LINE
```
