# Router EPS - Implementacao

Data: 2026-05-29

## Veredito

`router_eps` precisa ser um processo separado de `scara_hotwire_eps`. A SCARA/fio quente corta no plano usando o fio como linha de corte. A router/fresa usa ferramenta rotativa, Z, profundidade por passe, RPM, feed XY/Z e compensacao de raio.

## Base oficial usada

| Fonte | Ponto validado | Decisao |
| --- | --- | --- |
| [MachSupport - Mach3](https://www.machsupport.com/software/mach3/) | Mach3 processa G-code e e usado tambem para routers. | Gerar pacote com parametros de router e exigir dry-run. |
| [MachSupport - LazyCam downloads](https://www.machsupport.com/downloads-updates/mach3-downloads/) | LazyCam e importador beta de DXF/CMX para gerar G-code no Mach3. | Nao confiar em profundidade/compensacao sem teste real. |
| [Autodesk - DXF R12 Reference](https://damassets.autodesk.net/content/dam/autodesk/www/developer-network/platform-technologies/autocad-dxf-archive/acad_r12_dxf.pdf) | DXF R12 e intercâmbio por entidades/layers/group codes. | DXF de corte deve conter so geometria simples; PDF carrega instrucoes. |
| [ezdxf r12writer](https://ezdxf.readthedocs.io/en/stable/addons/r12writer.html) | `r12writer` cria desenhos R12 simples; nao suporta BLOCK/INSERT. | Usar entidades simples e validar denylist. |
| [LinuxCNC G-code overview](https://www.linuxcnc.org/docs/2.9/html/gcode/overview.html) | G-code e composto por linhas/blocos RS274/NGC; dialetos variam. | G-code router fica experimental e validado contra Mach3 real. |

## Diferencas de processo

| Tema | SCARA/fio quente | Router EPS |
| --- | --- | --- |
| `process_type` | `hotwire_2d` | `router_spindle` |
| Centro da geometria | linha do fio | centro da fresa |
| Compensacao | perda termica do fio | raio/diametro da fresa |
| Z | limitado/simples | obrigatorio |
| Passes | velocidade/temperatura | profundidade por passe |
| Parametros criticos | fio, velocidade, lead-in/out | fresa, Z seguro, RPM, feed XY/Z, plunge |
| Saida MVP | DXF + notas LazyCam/Mach3 | DXF + notas CAM/router + PDF de parametros |

## Contrato minimo do projeto router

```yaml
project:
  id: corte_router_eps_teste_001
  name: Corte router EPS teste
  unit: mm
  status: draft
  source:
    kind: manual_text
    dimensions_confirmed: true
    scale_confirmed: true
    production_confirmed: false

machine:
  profile: router_eps
  process_type: router_spindle
  output_format: dxf_r12
  cam_bridge: confirmar
  controller_hint: Mach3

material:
  type: EPS
  density: confirmar
  stock:
    length_x: 1000
    width_y: 500
    thickness_z: 100

tool:
  kind: endmill
  diameter_mm: 6
  effective_kerf_mm: 6
  flute_length_mm: confirmar
  max_depth_per_pass_mm: confirmar

cut:
  template: profile_2d
  origin: lower_left
  cut_plane: XY
  safe_margin_mm: 10
  compensation: centerline
  strategy: through_cut
  depth:
    z_safe_mm: confirmar
    final_depth_z: 105
    pass_depth_mm: confirmar
  feed:
    xy_mm_min: confirmar
    z_mm_min: confirmar
    spindle_rpm: confirmar

outputs:
  dxf: true
  svg_preview: true
  pdf_job: true
  manifest: true
  gcode:
    enabled: false
```

## Validador obrigatorio

Implementar `src/epscad/validators/router_validator.py` com estes bloqueios:

| Validacao | Regra |
| --- | --- |
| ferramenta | `tool.kind`, `diameter_mm`, `effective_kerf_mm` e `flute_length_mm` obrigatorios. |
| profundidade | `final_depth_z`, `pass_depth_mm` e `z_safe_mm` obrigatorios. |
| passe | `pass_depth_mm <= tool.max_depth_per_pass_mm`. |
| comprimento util | `tool.flute_length_mm >= final_depth_z`, salvo override documentado. |
| estoque | `final_depth_z <= stock.thickness_z + overcut_allowance_mm`. |
| feed/RPM | `feed.xy_mm_min`, `feed.z_mm_min` e `spindle_rpm` obrigatorios. |
| raio interno | cantos internos menores que `tool.diameter_mm / 2` exigem dogbone, raio maior ou bloqueio. |
| compensacao | `centerline` exige aviso no PDF/manifest de que o CAM precisa compensar. |

## Camadas DXF para router

```text
CUT_OUTSIDE
CUT_INSIDE
POCKET
DRILL
REFERENCE_DO_NOT_CUT
```

Regra: `REFERENCE_DO_NOT_CUT` pode aparecer em preview, mas deve ser bloqueado no DXF final de corte.

## Manifest router

```json
{
  "machine_profile": "router_eps",
  "process_type": "router_spindle",
  "tool_diameter_mm": 6,
  "final_depth_z": 105,
  "pass_depth_mm": 5,
  "z_safe_mm": 15,
  "feed_xy_mm_min": 1200,
  "feed_z_mm_min": 300,
  "spindle_rpm": 18000,
  "compensation_mode": "centerline",
  "cam_must_apply_tool_compensation": true,
  "gcode_enabled": false
}
```

## Pacote router

```text
outputs/<project_id>/
  00_README_OPERADOR.txt
  01_preview.svg
  02_ordem_router_eps.pdf
  03_cutpaths_router_r12.dxf
  04_cutpaths_router_2007.dxf
  05_project.locked.yaml
  06_manifest.json
  07_checklist_router.txt
  08_cam_import_notes.txt
  09_freecad_preview.FCStd
  10_validation_report.json
  11_hashes.sha256
  12_package_for_machine.zip
```

O PDF de router deve mostrar maquina/perfil, bloco X/Y/Z, fresa, diametro, profundidade final, profundidade por passe, origem, Z seguro, feed XY/Z, RPM, compensacao e status de producao.
