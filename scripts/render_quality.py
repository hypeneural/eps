"""Optional Blender Cycles quality render, independent of verified cutting ZIP."""
import argparse
import shutil
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--blender",default="blender")
    p.add_argument("--samples",type=int,default=64)
    a=p.parse_args()
    exe=shutil.which(a.blender)
    if not exe:
        p.error("Blender 4.2+ not found; use the existing CPU PNG or specify --blender")
    if not a.input.is_file() or a.input.suffix.lower()!=".glb" or a.output.suffix.lower()!=".png" or not 1<=a.samples<=512:
        p.error("Require existing GLB, PNG output and 1..512 samples")
    if a.output.name in ("26_render_eps.png","27_render_assembly.png","25_eps_material.png","28_eps_normal.png","01_preview.png"):
        p.error("Do not overwrite hashed preview; use a separate quality PNG")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([exe,"--background","--factory-startup","--python-exit-code","1","--python",str(ROOT/"scripts/blender/render_eps.py"),"--",str(a.input.resolve()),str(a.output.resolve()),str(a.samples)],check=True,timeout=900)
    if not a.output.is_file() or a.output.stat().st_size<100:
        raise RuntimeError("Blender did not produce PNG")
    print(a.output.resolve())
if __name__=="__main__":
    main()
