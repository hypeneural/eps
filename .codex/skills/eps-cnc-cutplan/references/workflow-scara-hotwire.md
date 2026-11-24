# Workflow SCARA Hotwire

SCARA/fio quente is the initial real-machine flow:

```text
project.yaml -> CutPath[] -> DXF R12 -> LazyCam -> Mach3/EPS -> dry-run -> cut
```

Required project fields:

- `machine.profile=scara_hotwire_eps`
- `machine.process_type=hotwire_2d`
- `process.hotwire.wire_mode=line_hotwire`
- `process.hotwire.wire_count`
- `process.hotwire.effective_kerf_mm`
- `process.hotwire.min_segment_mm`
- `process.hotwire.min_radius_mm`
- `process.feed.xy_mm_min`

Block production if any of these values are `confirmar`.

Do not use router/fresa concepts for the active SCARA workflow: no spindle, RPM, tool diameter, safe Z, pass depth, pocket, or router schema.

## Template TP40 (`tp40_core`)

- Se `cut.template=tp40_core`, ler `docs/11_TP40_TRAPEZOIDAL.md`.
- Medidas nominais ficam em `draft` com `profile_confirmed: false`; nunca marcar `profile_confirmed: true` sem medida real da telha.
- Linhas de referencia (`REF_STOCK`, `REF_NOMINAL`) so aparecem em preview/PDF/SVG, nunca no DXF.
