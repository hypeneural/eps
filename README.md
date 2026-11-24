# EPS SCARA Hotwire CutPlan

Repositorio para gerar pacotes de corte de EPS/isopor para SCARA CNC de fio quente/linha quente com Codex, Python, DXF R12 e validacoes bloqueantes.

> **Status:** funcional para gerar DXF de **teste**. Producao continua bloqueada ate o inventario real da maquina ser preenchido (ver `docs/12_AUDITORIA_E_PRONTIDAO.md`).

## Instalacao

```powershell
python -m pip install -r requirements.txt   # PyYAML, jsonschema, ezdxf
python -m unittest discover -s tests -p "test_*.py"
```

Python >= 3.11. Sem `ezdxf` o DXF ainda e gerado (escritor reserva com estrutura R12 completa), mas o recomendado e instalar.

## Fluxo ativo

```text
texto / foto / croqui
  -> Codex cria ou edita YAML
  -> Python valida schema + maquina + material + fio quente
  -> templates geram CutPath[]
  -> exportadores geram DXF/PDF/SVG/manifest
  -> operador confere no notebook
  -> LazyCam importa DXF
  -> Mach3/EPS faz dry-run
  -> SCARA corta EPS/isopor
```

## Processo suportado

- `scara_hotwire_eps`: SCARA/fio quente 2D.

Router/fresa, spindle, RPM, Z seguro, profundidade por passe e pocket 2.5D estao arquivados em `archive/router_spindle_eps/` como estudo futuro. Eles nao fazem parte do fluxo ativo da maquina atual.

## Templates

| Template | Uso | Exemplo |
| --- | --- | --- |
| `straight_cut` | linha reta de teste | `projects/exemplos/001_linha_500mm.yaml` |
| `square_test` | quadrado de calibracao | `projects/exemplos/002_quadrado_100mm.yaml` |
| `grid_blocks` | grade de blocos com linhas compartilhadas | `projects/exemplos/003_grade_blocos_100mm.yaml` |
| `profile_2d` | polilinha por pontos | - |
| `photo_trace` | rascunho de foto (sem geometria, sem DXF) | `projects/exemplos/005_foto_bloqueada.yaml` |
| `tp40_core` | miolo EPS de telha **TP40 trapezoidal** (topo plano + base trapezoidal) | `projects/exemplos/007_tp40_nucleo_eps.yaml` |

TP40: ver `docs/11_TP40_TRAPEZOIDAL.md` (parametros, como medir a telha, compensacao do fio, gates).

## Uso rapido

```powershell
python .\scripts\validate_project.py .\projects\exemplos\007_tp40_nucleo_eps.yaml
python .\scripts\generate_project.py .\projects\exemplos\007_tp40_nucleo_eps.yaml
python .\scripts\validate_dxf.py .\outputs\001_linha_500mm\03_cutpaths_r12.dxf
```

Saidas em `outputs/<project_id>/` (ignorado pelo git): preview PNG/SVG, PDF de ordem de corte, DXF R12 (quando o status permite), manifest, hashes e ZIP.

## Docs principais

- `AGENTS.md`
- `IMPLEMENTACAO_EPS_CNC.md`
- `VALIDACAO_OFICIAL_E_MELHORIAS.md`
- `docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md`
- `docs/02_INVENTARIO_MAQUINA_SCARA.md`
- `docs/08_BACKUP_PC_MACH3_PERFIL_EPS.md`
- `docs/11_TP40_TRAPEZOIDAL.md`
- `docs/12_AUDITORIA_E_PRONTIDAO.md`
- `docs/DECISOES_TECNICAS.md`

## Comandos alvo

```powershell
python .\scripts\validate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\generate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\validate_dxf.py .\outputs\001_linha_500mm\03_cutpaths_r12.dxf
python -m unittest discover -s tests -p "test_*.py"
```

## TP40: pacote 3D e corte remoto
```powershell
python -m pip install -r requirements.txt
python scripts/new_tp40.py tp40_980_sks --length 1000 --thickness 30
python scripts/new_tp40.py tp40_1020_isoeste --length 1000 --thickness 30
```
Abertura em outputs/<variante>/26_render_eps.png e 27_render_assembly.png.
GLB em metros, STL em mm. Nenhum 3D vai para o LazyCam.
Catalogos sao referencias e nunca liberam DXF automaticamente. Veja docs/13_TP40_3D_REMOTE.md.

## Antigravity: primeiro teste completo
```powershell
python -m pip check
python -m unittest discover -s tests -p "test_*.py"
python scripts/first_test.py --output outputs/primeiro_teste
```
DXF de 500 mm e calibracao, as duas TP40 sao referencias sem DXF. Consulte docs/14_ANTIGRAVITY_LOCAL.md e skills em .agents/skills. Render Cycles opcional: scripts/render_quality.py --help.

O primeiro teste inclui tambem trapezio_sintetico_400mm: 9 LINE, 400 x 40 mm, somente importacao/dry-run sem calor. Nao representa TP40 comercial.

## Revisao de desenhos historicos
Veja docs/15_HISTORICAL_EVIDENCE.md e `python scripts/review_historical_roof.py --help`. A recuperacao e exclusivamente visual e mantem evidencias originais locais.

## Desenvolvimento separado da fabrica: TP40 base lisa
`powershell -NoProfile -File scripts/prepare_development.ps1` no PC moderno. Sem necessidade de acessar o PC da CNC. Perfil nominal com microdobra disponivel no catalogo; `python scripts/prepare_tp40.py --help`. Evidencia original opcional em private_evidence/. Veja docs/16_DEVELOPMENT_HANDOFF.md. ZIP de revisao sem DXF/TAP.

## Galeria Iso Nunes
`python scripts/gallery_demo.py --output outputs/portal_demo` gera TP40 nominal, página estática, miniaturas e GLB. Veja docs/17_PORTAL_ISONUNES.md para logo, registro local e FTPS. Sem banco ou PHP obrigatório. Nenhum corte comercial liberado automaticamente.
