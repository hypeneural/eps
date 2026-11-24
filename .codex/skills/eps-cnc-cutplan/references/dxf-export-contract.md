# DXF Export Contract

Primary DXF: R12.

Allowed in final cutting DXF:

- `LINE`
- `ARC`
- `CIRCLE`
- `POLYLINE`, `VERTEX`, `SEQEND`

Forbidden in final cutting DXF:

- `SPLINE`
- `HATCH`
- `TEXT`
- `MTEXT`
- `DIMENSION`
- `INSERT`
- `BLOCK` output content
- `ELLIPSE`
- `3DFACE`
- `SOLID`
- 3D entities

Text, dimensions, arrows, origin labels, and notes belong in SVG/PDF previews, not cutting DXF.
