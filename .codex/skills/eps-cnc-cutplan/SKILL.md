---
name: eps-cnc-cutplan
description: Use when creating, validating, or improving EPS/isopor CNC cut plans for the SCARA hotwire workflow, including YAML schemas, DXF export contracts, image-to-cutpath drafts, calibration, manifests, and production gates.
---

# EPS CNC CutPlan

## Fast Path

1. Confirm `machine.profile=scara_hotwire_eps` and `machine.process_type=hotwire_2d`.
2. For flow/output/delivery changes, read `docs/00_FLUXO_CODEX_SCARA_HOTWIRE.md`.
3. Edit YAML, schemas, validators, templates, or docs; never generate DXF/G-code directly in chat.
4. Validate `unit=mm`, machine profile, material stock, hotwire data, bbox, production status, and `confirmar` fields.
5. Generate only deterministic outputs from `CutJobResult -> CutPath[] -> exporters`.
6. Keep G-code disabled unless experimental gates, golden samples, dry-run, and operator confirmation exist.

## Process Rules

- Hotwire: require wire mode, wire count, effective kerf, lead-in/out, min segment/radius, and feed.
- The current SCARA is not a router/fresa workflow. Do not add spindle, RPM, tool diameter, safe Z, pass depth, pocket, or router fields to active projects.
- Image input: always draft until scale and dimensions are confirmed.
- DXF final: no text, dimensions, hatches, blocks, splines, ellipses, or 3D entities.

## References

Use progressive disclosure:

- If `machine.profile=scara_hotwire_eps`, read `references/workflow-scara-hotwire.md`.
- If `project.source.kind=image_reference`, read `references/image-to-cutpath.md`.
- If touching DXF exporters or validators, read `references/dxf-export-contract.md`.
- If touching output packaging or final delivery, read `references/delivery-and-preview.md`.
- Do not load every reference by default.

## Helper Scripts

- `scripts/inspect_project.py <project.yaml>` summarizes profile, process, schema, and G-code flag.
- `scripts/list_confirmar_fields.py <project.yaml>` lists blocking `confirmar` fields.
- `scripts/explain_failed_gate.py <project-or-profile.yaml>` explains common production gates.
- `scripts/summarize_validation.py <validation_report.json>` summarizes validation output.
