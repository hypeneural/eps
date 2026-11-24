# Delivery and Preview

Use this reference when changing outputs or preparing the final response.

Generated package:

```text
outputs/<project_id>/
  01_preview.svg
  01_preview.png
  02_ordem_corte_eps.pdf
  03_cutpaths_r12.dxf
  06_manifest.json
  12_package_for_machine.zip
```

For visual delivery in the Codex app, show the PNG with an absolute path:

```markdown
![preview](/C:/Users/Anderson/Desktop/EPS/outputs/<project_id>/01_preview.png)
```

PDF order requirements:

- Show strong status warning: preliminary/test/production.
- Show project, machine profile, material stock and origin.
- Show hotwire fields: wire mode/count, kerf, lead-in/out, min segment/radius and feed.
- Show bbox and a vector preview.
- Include LazyCam and Mach3/EPS checklists.
- For image-reference drafts, state that no production DXF is released until scale and measures are confirmed.

Rules:

- PNG/SVG/PDF are for inspection.
- DXF R12 is the LazyCam input.
- ZIP is the transfer package.
- Draft/image-reference projects may produce PNG/SVG/PDF but must not produce DXF.
