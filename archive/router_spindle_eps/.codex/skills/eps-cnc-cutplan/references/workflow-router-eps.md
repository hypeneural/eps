# Workflow Router EPS

Router EPS requires a separate production gate from hotwire.

Required project fields:

- `machine.profile=router_eps`
- `machine.process_type=router_spindle`
- `tool.kind`
- `tool.diameter_mm`
- `tool.effective_kerf_mm`
- `tool.flute_length_mm`
- `tool.max_depth_per_pass_mm`
- `cut.depth.z_safe_mm`
- `cut.depth.final_depth_z`
- `cut.depth.pass_depth_mm`
- `cut.feed.xy_mm_min`
- `cut.feed.z_mm_min`
- `cut.feed.spindle_rpm`

Block production if any of these values are `confirmar`.

PDF and manifest must state whether compensation is centerline/CAM-side or geometry-offset-applied.
