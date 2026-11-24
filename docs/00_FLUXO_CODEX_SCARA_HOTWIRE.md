# Fluxo Codex - SCARA Hotwire EPS

Data: 2026-05-29

Este runbook e o caminho curto para o Codex entender, gerar, validar e entregar um pacote de corte EPS/isopor para a SCARA CNC de fio quente/linha quente.

## Regra principal

```text
Codex interpreta e edita YAML/codigo.
Python valida e gera CutPath[].
Exportadores escrevem SVG, PNG, PDF, DXF, manifest e ZIP.
Operador confere LazyCam/Mach3 antes de cortar.
```

O fluxo ativo e sempre:

```text
project.yaml
  -> validate_project
  -> build_job
  -> geometry_validator
  -> exporters
  -> LazyCam
  -> Mach3/EPS
```

## Decisao por tipo de entrada

| Entrada do usuario | Acao do Codex | Saida permitida |
| --- | --- | --- |
| Texto com medidas | Criar/editar YAML hotwire | pacote se validar |
| Foto/croqui sem escala | Criar YAML `draft` com `image_reference` | SVG/PNG/PDF preliminar, sem DXF |
| Foto com medida real | Criar YAML `draft`, registrar medida e pedir confirmacao | preview preliminar |
| DXF/SVG existente | Registrar como referencia e validar medidas | DXF novo apenas apos validacao |
| Pedido de G-code | Bloquear no MVP | explicar golden samples/dry-run |
| Pedido com fresa/RPM/Z | Bloquear no fluxo SCARA | explicar que router esta arquivado |

## Arquivos de entrada

```text
projects/exemplos/<project_id>.yaml
machine_profiles/scara_hotwire_eps.yaml
schemas/project_hotwire.schema.json
schemas/machine_profile_hotwire.schema.json
```

## Arquivos de saida

```text
outputs/<project_id>/
  00_README_OPERADOR.txt
  01_preview.svg
  01_preview.png
  02_ordem_corte_eps.pdf
  03_cutpaths_r12.dxf
  05_project.locked.yaml
  06_manifest.json
  08_cam_import_notes.txt
  10_validation_report.json
  11_hashes.sha256
  12_package_for_machine.zip
```

`03_cutpaths_r12.dxf` so aparece quando o status permite DXF e nao ha erro.

## Entrega visual no Codex

Quando responder no Codex app, usar o PNG gerado para visualizacao direta:

```markdown
![preview](/C:/Users/Anderson/Desktop/EPS/outputs/<project_id>/01_preview.png)
```

Use caminho absoluto. O operador pode abrir:

- `01_preview.png` para inspecao visual rapida;
- `01_preview.svg` para preview vetorial;
- `02_ordem_corte_eps.pdf` para ordem tecnica, preview cotado e checklist LazyCam/Mach3;
- `03_cutpaths_r12.dxf` para LazyCam;
- `12_package_for_machine.zip` para levar o pacote completo.

## Comandos padrao

```powershell
python .\scripts\validate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\generate_project.py .\projects\exemplos\001_linha_500mm.yaml
python .\scripts\validate_dxf.py .\outputs\001_linha_500mm\03_cutpaths_r12.dxf
python -m unittest discover -s tests -p "test_*.py"
```

## Checklist antes de concluir

- `validate_project` sem erro.
- `generate_project` gerou `01_preview.png`.
- `02_ordem_corte_eps.pdf` contem alerta de status, bloco EPS, fio, feed, bbox e checklist LazyCam/Mach3.
- `validate_dxf` passou quando houver DXF.
- Foto sem escala nao gerou DXF.
- `manifest.json` lista `png_preview`.
- ZIP contem `01_preview.png`.
- Testes passam.

## Duvidas reais ainda abertas

- Area util X/Y/Z real da SCARA.
- Origem real e politica de zero no Mach3/EPS.
- Direcao positiva de X/Y.
- Quantidade real de fios/linhas.
- Perda efetiva do fio quente.
- Feed reto e feed curva seguros.
- Se LazyCam interpreta melhor ARC real ou linhas segmentadas.
- Extensao G-code real usada no Mach3.
- Golden samples reais em `samples/real_machine/`.
