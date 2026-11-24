"""Blender 4.2+ headless studio scene; input GLB is unchanged."""
import sys
import bpy
from mathutils import Vector
from pathlib import Path

source,output,samples=sys.argv[sys.argv.index("--")+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source)
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=="MESH"]
if not objects:
    raise ValueError("No mesh in GLB")
points=[o.matrix_world@Vector(v) for o in objects for v in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(lo+hi)/2
span=max(hi-lo)
if span<=0:
    raise ValueError("Empty bounds")
for obj in objects:
    for mat in obj.data.materials:
        if not mat or not mat.name.startswith("EPS"):
            continue
        mat.use_nodes=True
        nodes=mat.node_tree.nodes
        links=mat.node_tree.links
        bsdf=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
        coord=nodes.new("ShaderNodeTexCoord")
        vor=nodes.new("ShaderNodeTexVoronoi")
        vor.feature="DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value=420.0
        links.new(coord.outputs["Object"],vor.inputs["Vector"])
        ramp=nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position=.015
        ramp.color_ramp.elements[0].color=(.62,.64,.65,1)
        ramp.color_ramp.elements[1].position=.13
        ramp.color_ramp.elements[1].color=(.94,.95,.95,1)
        links.new(vor.outputs["Distance"],ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"],bsdf.inputs["Base Color"])
        bump=nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.3
        bump.inputs["Distance"].default_value=.0003
        links.new(vor.outputs["Distance"],bump.inputs["Height"])
        links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value=.86
        bsdf.inputs["Metallic"].default_value=0
bpy.ops.mesh.primitive_plane_add(size=span*20,location=(center.x,center.y,lo.z-.003*span))
ground=bpy.context.object
mat=bpy.data.materials.new("Studio matte")
mat.diffuse_color=(.21,.25,.30,1)
ground.data.materials.append(mat)
def point_at(obj,target):
    obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()
def area(name,offset,power,size):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power*span*span
    data.shape="DISK"
    data.size=size*span
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=center+Vector(offset)*span
    point_at(obj,center)
area("Key",(-1,-1,2),1000,1.5)
area("Fill",(1,-.5,.9),550,1.3)
area("Rim",(.2,1.5,1.7),900,1)
cam_data=bpy.data.cameras.new("Product camera")
cam=bpy.data.objects.new("Product camera",cam_data)
scene.collection.objects.link(cam)
cam.location=center+Vector((1.25,-2,1.15))*span
point_at(cam,center)
cam_data.type="ORTHO"
cam_data.ortho_scale=2.0*span
scene.camera=cam
scene.world=bpy.data.worlds.new("Studio world")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.45,.49,.55,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.35
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=int(samples)
scene.cycles.use_denoising=True
scene.render.resolution_x=1800
scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(Path(output))
bpy.ops.render.render(write_still=True)
