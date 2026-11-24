"""Export nominal geometry; never exports machine paths."""
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual.texture import TextureVisuals
from trimesh.visual.material import PBRMaterial
from epscad.visual.materials import eps_texture, eps_normal
from epscad.visual.render import render_roof

def mesh_mm(polygon,length):
    mesh=trimesh.creation.extrude_polygon(polygon,height=length,engine="earcut")
    if not mesh.is_watertight or not mesh.is_volume:
        raise ValueError("Invalid solid mesh")
    if not np.isclose(mesh.volume,polygon.area*length,rtol=1e-7):
        raise ValueError("Extrusion volume mismatch")
    return mesh

def _eps_visual(mesh):
    triangles=mesh.vertices[mesh.faces]
    vertices=triangles.reshape(-1,3)
    faces=np.arange(len(vertices)).reshape(-1,3)
    uv=[]
    for triangle,normal in zip(triangles,mesh.face_normals):
        axes=[i for i in range(3) if i!=int(np.argmax(np.abs(normal)))]
        uv.extend(triangle[:,axes]/80.0)
    material=PBRMaterial(name="EPS_white_beads",baseColorTexture=eps_texture(),normalTexture=eps_normal(),roughnessFactor=.88,metallicFactor=0.0)
    return trimesh.Trimesh(vertices=vertices/1000.0,faces=faces,visual=TextureVisuals(uv=np.asarray(uv),material=material),process=False)

def write_roof_assets(roof,output,status):
    out=Path(output)
    core=mesh_mm(roof.core,roof.length_mm)
    metal=mesh_mm(roof.metal,roof.length_mm)
    complement=mesh_mm(roof.complement,roof.length_mm)
    files={}
    def target(key,name):
        p=out/name
        files[key]=str(p)
        return p
    core.export(target("core_stl","20_eps_core_mm.stl"))
    complement.export(target("complement_stl","21_eps_complement_mm.stl"))
    metal.export(target("metal_reference_stl","22_metal_reference_mm.stl"))
    scene=trimesh.Scene()
    scene.add_geometry(_eps_visual(core),node_name="EPS",geom_name="EPS")
    visual_metal=metal.copy()
    visual_metal.apply_scale(.001)
    visual_metal.visual=TextureVisuals(material=PBRMaterial(name="Galvalume_reference",baseColorFactor=[.58,.62,.66,1],metallicFactor=.8,roughnessFactor=.38))
    scene.add_geometry(visual_metal,node_name="METAL_REFERENCE",geom_name="METAL_REFERENCE")
    target("assembly_glb","23_assembly_reference.glb").write_bytes(scene.export(file_type="glb"))
    target("eps_glb","24_eps_core.glb").write_bytes(trimesh.Scene(_eps_visual(core)).export(file_type="glb"))
    eps_texture().save(target("eps_texture","25_eps_material.png"))
    eps_normal().save(target("eps_normal","28_eps_normal.png"))
    render_roof(roof,target("render_eps","26_render_eps.png"),status=status)
    render_roof(roof,target("render_assembly","27_render_assembly.png"),assembly=True,status=status)
    return files
