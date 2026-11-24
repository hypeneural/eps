"""Blender 4.2+ headless studio scene; input GLB is unchanged."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

VALID_VIEWS = (
    "perspective",
    "section_front",
    "microgroove_detail",
    "assembly",
    "exploded",
    "texture_closeup",
)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :]
    if len(argv) < 3:
        raise ValueError("Expected: <input.glb> <output.png> <samples> [view]")
    source, output, samples = argv[0], argv[1], int(argv[2])
    view = argv[3] if len(argv) >= 4 else "perspective"
    if view not in VALID_VIEWS:
        raise ValueError(f"Unsupported view {view!r}; expected one of {VALID_VIEWS}")
    return source, output, samples, view


def configure_cycles_device(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = backend
                prefs.get_devices()
                gpu_devices = [d for d in prefs.devices if d.type == backend]
                if gpu_devices:
                    for d in prefs.devices:
                        d.use = d.type == backend
                    scene.cycles.device = "GPU"
                    return backend
            except Exception:
                continue
    except Exception:
        pass
    return "CPU"


def set_input(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def build_eps_material(mat):
    """Procedural white expanded polystyrene with rounded fused beads and micro-relief."""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    coord = nodes.new("ShaderNodeTexCoord")

    # Primary EPS fused beads (~2.8 mm diameter in meters -> scale ~360)
    vor_f1 = nodes.new("ShaderNodeTexVoronoi")
    vor_f1.feature = "F1"
    vor_f1.inputs["Scale"].default_value = 360.0
    set_input(vor_f1, "Randomness", 0.85)
    links.new(coord.outputs["Object"], vor_f1.inputs["Vector"])

    # Narrow fusion seams between adjacent beads (matching scale & randomness)
    vor_edge = nodes.new("ShaderNodeTexVoronoi")
    vor_edge.feature = "DISTANCE_TO_EDGE"
    vor_edge.inputs["Scale"].default_value = 360.0
    set_input(vor_edge, "Randomness", 0.85)
    links.new(coord.outputs["Object"], vor_edge.inputs["Vector"])

    # Fine chalky micro-porosity on cut EPS surface
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1800.0
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.65
    links.new(coord.outputs["Object"], noise.inputs["Vector"])

    # Subtle per-bead white brightness variation (real fused EPS beads)
    bead_bw = nodes.new("ShaderNodeRGBToBW")
    links.new(vor_f1.outputs["Color"], bead_bw.inputs["Color"])
    bead_ramp = nodes.new("ShaderNodeValToRGB")
    bead_ramp.color_ramp.elements[0].position = 0.0
    bead_ramp.color_ramp.elements[0].color = (0.81, 0.82, 0.825, 1.0)
    bead_ramp.color_ramp.elements[1].position = 1.0
    bead_ramp.color_ramp.elements[1].color = (0.95, 0.955, 0.95, 1.0)
    links.new(bead_bw.outputs["Val"], bead_ramp.inputs["Fac"])

    # Smooth narrow bead fusion crevices (color darkening)
    seam_col = nodes.new("ShaderNodeMapRange")
    seam_col.interpolation_type = "SMOOTHSTEP"
    seam_col.inputs["From Min"].default_value = 0.006
    seam_col.inputs["From Max"].default_value = 0.088
    seam_col.inputs["To Min"].default_value = 0.0
    seam_col.inputs["To Max"].default_value = 1.0
    links.new(vor_edge.outputs["Distance"], seam_col.inputs["Value"])

    mix_col = nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.inputs["A"].default_value = (0.58, 0.60, 0.62, 1.0)
    links.new(seam_col.outputs["Result"], mix_col.inputs["Factor"])
    links.new(bead_ramp.outputs["Color"], mix_col.inputs["B"])
    links.new(mix_col.outputs["Result"], bsdf.inputs["Base Color"])

    # Smooth spherical bead pillow: 1 - d^2 (zero slope at bead center, no sharp cone!)
    d_sq = nodes.new("ShaderNodeMath")
    d_sq.operation = "POWER"
    d_sq.inputs[1].default_value = 2.0
    links.new(vor_f1.outputs["Distance"], d_sq.inputs[0])

    dome = nodes.new("ShaderNodeMapRange")
    dome.interpolation_type = "SMOOTHSTEP"
    dome.inputs["From Min"].default_value = 0.0
    dome.inputs["From Max"].default_value = 0.65
    dome.inputs["To Min"].default_value = 1.0
    dome.inputs["To Max"].default_value = 0.0
    links.new(d_sq.outputs["Value"], dome.inputs["Value"])

    # Soft rounded bead shoulder at fusion seam
    seam_h = nodes.new("ShaderNodeMapRange")
    seam_h.interpolation_type = "SMOOTHSTEP"
    seam_h.inputs["From Min"].default_value = 0.0
    seam_h.inputs["From Max"].default_value = 0.14
    seam_h.inputs["To Min"].default_value = 0.0
    seam_h.inputs["To Max"].default_value = 1.0
    links.new(vor_edge.outputs["Distance"], seam_h.inputs["Value"])

    dome_w = nodes.new("ShaderNodeMath")
    dome_w.operation = "MULTIPLY"
    dome_w.inputs[1].default_value = 0.38
    links.new(dome.outputs["Result"], dome_w.inputs[0])

    seam_w = nodes.new("ShaderNodeMath")
    seam_w.operation = "MULTIPLY"
    seam_w.inputs[1].default_value = 0.52
    links.new(seam_h.outputs["Result"], seam_w.inputs[0])

    bead_h = nodes.new("ShaderNodeMath")
    bead_h.operation = "ADD"
    links.new(dome_w.outputs["Value"], bead_h.inputs[0])
    links.new(seam_w.outputs["Value"], bead_h.inputs[1])

    grain_w = nodes.new("ShaderNodeMath")
    grain_w.operation = "MULTIPLY"
    grain_w.inputs[1].default_value = 0.10
    links.new(noise.outputs["Fac"], grain_w.inputs[0])

    height_total = nodes.new("ShaderNodeMath")
    height_total.operation = "ADD"
    links.new(bead_h.outputs["Value"], height_total.inputs[0])
    links.new(grain_w.outputs["Value"], height_total.inputs[1])

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.44
    bump.inputs["Distance"].default_value = 0.00095
    links.new(height_total.outputs["Value"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    rough_map = nodes.new("ShaderNodeMapRange")
    rough_map.inputs["To Min"].default_value = 0.76
    rough_map.inputs["To Max"].default_value = 0.90
    links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
    links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])

    set_input(bsdf, "Metallic", 0.0)
    set_input(bsdf, "Specular IOR Level", 0.34)
    set_input(bsdf, "Subsurface Weight", 0.0)


def build_metal_material(mat):
    """Galvalume / Aluzinco satin metallic reference sheet with fine spangle."""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    coord = nodes.new("ShaderNodeTexCoord")

    spangle = nodes.new("ShaderNodeTexVoronoi")
    spangle.feature = "F1"
    spangle.inputs["Scale"].default_value = 180.0
    links.new(coord.outputs["Object"], spangle.inputs["Vector"])

    bw = nodes.new("ShaderNodeRGBToBW")
    links.new(spangle.outputs["Color"], bw.inputs["Color"])

    col_ramp = nodes.new("ShaderNodeValToRGB")
    col_ramp.color_ramp.elements[0].position = 0.0
    col_ramp.color_ramp.elements[0].color = (0.48, 0.52, 0.57, 1.0)
    col_ramp.color_ramp.elements[1].position = 1.0
    col_ramp.color_ramp.elements[1].color = (0.72, 0.76, 0.81, 1.0)
    links.new(bw.outputs["Val"], col_ramp.inputs["Fac"])
    links.new(col_ramp.outputs["Color"], bsdf.inputs["Base Color"])

    rough_map = nodes.new("ShaderNodeMapRange")
    rough_map.inputs["To Min"].default_value = 0.20
    rough_map.inputs["To Max"].default_value = 0.34
    links.new(bw.outputs["Val"], rough_map.inputs["Value"])
    links.new(rough_map.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.035
    bump.inputs["Distance"].default_value = 0.0001
    links.new(bw.outputs["Val"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    set_input(bsdf, "Metallic", 0.92)


def world_bounds(objects):
    points = [o.matrix_world @ Vector(v) for o in objects for v in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return lo, hi


def is_eps_object(obj):
    if "EPS" in obj.name.upper():
        return True
    return any(m and m.name.upper().startswith("EPS") for m in obj.data.materials)


def point_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_area_light(scene, name, location, target, energy, size, color=(1.0, 1.0, 1.0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    point_at(obj, target)
    return obj


def _make_backdrop_material(color=(0.24, 0.27, 0.31, 1.0), roughness=0.90):
    gmat = bpy.data.materials.new("StudioBackdrop")
    gmat.use_nodes = True
    gbsdf = next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gbsdf.inputs["Base Color"].default_value = color
    gbsdf.inputs["Roughness"].default_value = roughness
    set_input(gbsdf, "Specular IOR Level", 0.14)
    return gmat


def build_cyclorama(scene, lo, hi):
    """Seamless curved L-sweep studio cyclorama (eliminates harsh horizon line)."""
    size = hi - lo
    center = (lo + hi) / 2.0
    span = max(size.x, size.y, size.z)

    z_floor = lo.z - 0.0006
    half_w = span * 16.0
    y_front = center.y - span * 8.0
    y_curve_start = hi.y + span * 1.15
    radius = span * 2.2
    z_top = z_floor + radius + span * 6.0
    segments = 32

    profile = [(y_front, z_floor), (y_curve_start, z_floor)]
    for i in range(1, segments + 1):
        theta = (math.pi / 2.0) * (i / segments)
        py = y_curve_start + radius * math.sin(theta)
        pz = z_floor + radius * (1.0 - math.cos(theta))
        profile.append((py, pz))
    y_wall = y_curve_start + radius
    profile.append((y_wall, z_top))

    verts = []
    faces = []
    for py, pz in profile:
        verts.append((center.x - half_w, py, pz))
        verts.append((center.x + half_w, py, pz))
    for i in range(len(profile) - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("StudioCycloramaMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new("StudioCyclorama", mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(_make_backdrop_material((0.26, 0.29, 0.34, 1.0), roughness=0.92))
    return obj


def build_studio_backdrop(scene, lo, hi, view):
    """Use seamless cyclorama on 3D hero views and clean studio floor elsewhere."""
    size = hi - lo
    center = (lo + hi) / 2.0
    span = max(size.x, size.y, size.z)

    if view in ("perspective", "assembly", "exploded"):
        build_cyclorama(scene, lo, hi)
    else:
        bpy.ops.mesh.primitive_plane_add(
            size=span * 40.0,
            location=(center.x, center.y, lo.z - 0.0006),
        )
        ground = bpy.context.object
        ground.data.materials.append(_make_backdrop_material((0.20, 0.23, 0.27, 1.0), roughness=0.88))

    scene.world = bpy.data.worlds.new("StudioWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.24, 0.27, 0.32, 1.0)
    bg.inputs[1].default_value = 0.50


def setup_studio(scene, lo, hi, view):
    size = hi - lo
    center = (lo + hi) / 2.0
    span = max(size.x, size.y, size.z)

    build_studio_backdrop(scene, lo, hi, view)

    if view == "texture_closeup":
        focus = Vector((lo.x + 0.28 * size.x, lo.y + 0.04, hi.z - 0.010))
        add_area_light(scene, "Key", focus + Vector((-0.55, -0.20, 0.20)), focus, 17.0, 0.18, (1.0, 0.97, 0.93))
        add_area_light(scene, "Fill", focus + Vector((0.55, -0.45, 0.42)), focus, 7.0, 0.50, (0.88, 0.94, 1.0))
        add_area_light(scene, "Rim", focus + Vector((0.15, 0.45, 0.32)), focus, 11.0, 0.30, (1.0, 1.0, 1.0))
    elif view == "microgroove_detail":
        focus = Vector((lo.x + 0.484 * size.x, lo.y + 0.04, lo.z + 0.032))
        # Grazing low-side key accentuates fused white EPS beads right around the 48 x 2 mm step
        add_area_light(scene, "Key", focus + Vector((-0.68, -0.20, 0.22)), focus, 10.5, 0.16, (1.0, 0.975, 0.94))
        add_area_light(scene, "Fill", focus + Vector((0.65, -0.42, 0.28)), focus, 3.8, 0.45, (0.88, 0.94, 1.0))
        # Soft low bounce illuminates the Galvalume metallic negative beneath the microgroove
        add_area_light(scene, "MetalBounce", focus + Vector((-0.04, -0.48, -0.04)), focus + Vector((0.0, 0.08, -0.005)), 12.0, 0.28, (0.95, 0.98, 1.0))
    elif view == "section_front":
        target = Vector((center.x, lo.y, center.z))
        add_area_light(scene, "Key", target + Vector((-1.35 * span, -1.05 * span, 0.65 * span)), target, 140.0 * span * span, 0.75 * span, (1.0, 0.985, 0.96))
        add_area_light(scene, "Fill", target + Vector((1.25 * span, -1.20 * span, 0.40 * span)), target, 52.0 * span * span, 1.3 * span, (0.88, 0.94, 1.0))
        add_area_light(scene, "UnderMetal", target + Vector((0.15 * span, -0.85 * span, -0.25 * span)), target, 32.0 * span * span, 0.9 * span, (0.95, 0.98, 1.0))
    elif view == "assembly":
        add_area_light(scene, "Key", center + Vector((-1.45, -1.75, 1.15)) * span, center, 165.0 * span * span, 0.95 * span, (1.0, 0.985, 0.96))
        add_area_light(scene, "Fill", center + Vector((1.55, -1.25, 0.70)) * span, center, 68.0 * span * span, 1.40 * span, (0.88, 0.94, 1.0))
        add_area_light(scene, "ChannelBounce", Vector((center.x, lo.y - 1.05 * span, lo.z + 0.04 * span)), Vector((center.x, lo.y + 0.25 * size.y, lo.z + 0.02)), 55.0 * span * span, 0.65 * span, (0.96, 0.98, 1.0))
        add_area_light(scene, "Rim", center + Vector((0.25, 1.75, 1.10)) * span, center, 125.0 * span * span, 0.95 * span, (1.0, 1.0, 1.0))
    else:
        add_area_light(scene, "Key", center + Vector((-1.45, -1.75, 1.25)) * span, center, 165.0 * span * span, 0.95 * span, (1.0, 0.985, 0.96))
        add_area_light(scene, "Fill", center + Vector((1.65, -1.15, 0.85)) * span, center, 62.0 * span * span, 1.45 * span, (0.88, 0.94, 1.0))
        add_area_light(scene, "Rim", center + Vector((0.25, 1.75, 1.15)) * span, center, 125.0 * span * span, 0.95 * span, (1.0, 1.0, 1.0))


def setup_camera(scene, lo, hi, view):
    size = hi - lo
    center = (lo + hi) / 2.0
    span = max(size.x, size.y, size.z)

    cam_data = bpy.data.cameras.new("ProductCamera")
    cam = bpy.data.objects.new("ProductCamera", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    res_x, res_y = 1600, 1000

    if view == "perspective":
        cam_data.type = "PERSP"
        cam_data.lens = 55.0
        target = Vector((center.x, center.y - 0.04 * size.y, center.z - 0.005))
        cam.location = target + Vector((-0.88 * span, -2.05 * span, 0.56 * span))
        point_at(cam, target)
    elif view == "assembly":
        cam_data.type = "PERSP"
        cam_data.lens = 52.0
        target = Vector((center.x, center.y - 0.04 * size.y, center.z - 0.004))
        cam.location = target + Vector((0.62 * span, -2.20 * span, 0.30 * span))
        point_at(cam, target)
    elif view == "exploded":
        cam_data.type = "PERSP"
        cam_data.lens = 52.0
        target = Vector((center.x, center.y - 0.05 * size.y, center.z))
        cam.location = target + Vector((-0.85 * span, -2.10 * span, 0.50 * span))
        point_at(cam, target)
    elif view == "section_front":
        res_x, res_y = 1920, 680
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = size.x * 1.08
        target = Vector((center.x, lo.y, center.z))
        cam.location = Vector((center.x, lo.y - 1.6 * span, center.z))
        point_at(cam, target)
    elif view == "microgroove_detail":
        cam_data.type = "PERSP"
        cam_data.lens = 85.0
        target = Vector((lo.x + 0.484 * size.x, lo.y + 0.045, lo.z + 0.032))
        cam.location = target + Vector((-0.070, -0.285, 0.014))
        point_at(cam, target)
    elif view == "texture_closeup":
        cam_data.type = "PERSP"
        cam_data.lens = 90.0
        target = Vector((lo.x + 0.28 * size.x, lo.y + 0.045, hi.z - 0.012))
        cam.location = target + Vector((-0.052, -0.155, 0.068))
        point_at(cam, target)

    cam_data.clip_start = 0.005
    cam_data.clip_end = max(100.0, span * 200.0)
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100


def main():
    source, output, samples, view = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=source)
    scene = bpy.context.scene
    objects = [o for o in scene.objects if o.type == "MESH"]
    if not objects:
        raise ValueError("No mesh in GLB")

    for obj in objects:
        for mat in obj.data.materials:
            if not mat:
                continue
            name = mat.name.upper()
            if name.startswith("EPS"):
                build_eps_material(mat)
            elif "GALVALUME" in name or "METAL" in name:
                build_metal_material(mat)

    if view == "exploded":
        lo0, hi0 = world_bounds(objects)
        lift = max(0.070, (hi0.z - lo0.z) * 1.15)
        eps_objs = [o for o in objects if is_eps_object(o)]
        for obj in eps_objs:
            obj.location.z += lift
        bpy.context.view_layer.update()

    lo, hi = world_bounds(objects)
    if max(hi - lo) <= 0:
        raise ValueError("Empty bounds")

    setup_studio(scene, lo, hi, view)
    setup_camera(scene, lo, hi, view)

    device = configure_cycles_device(scene)
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.use_denoising = True
    if device == "OPTIX":
        try:
            scene.cycles.denoiser = "OPTIX"
        except Exception:
            pass
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = -0.35 if view == "microgroove_detail" else 0.0

    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(Path(output))
    print(f"Rendering view={view} device={device} samples={samples} -> {output}", flush=True)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
