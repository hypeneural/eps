"""Create a nominal TP40 project from a sourced catalog; never approve it."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from epscad.loader import load_yaml
from epscad.build import build_job
from epscad.exporters import write_outputs

def main():
    p=argparse.ArgumentParser()
    p.add_argument("variant",choices=["tp40_980_sks","tp40_1020_isoeste"])
    p.add_argument("--length",type=float,default=1000)
    p.add_argument("--thickness",type=float,default=30)
    args=p.parse_args()
    ref=load_yaml(ROOT/"catalogs"/"roof_profiles"/(args.variant+".yaml"))
    spec=load_yaml(ROOT/"projects"/"exemplos"/"007_tp40_nucleo_eps.yaml")
    params=dict(ref["profile"])
    params.update(min_thickness_mm=args.thickness,metal_thickness_mm=ref["metal_thickness_mm"])
    spec["project"].update(id=args.variant,name=args.variant+" - REFERENCIA NOMINAL")
    spec["cut"]["template_params"]=params
    spec["material"]["stock"].update(length_x=params["panel_width_mm"],height_y=params["profile_height_mm"]+args.thickness+30,thickness_z=args.length)
    spec["project"]["source"].update(scale_confirmed=False,dimensions_confirmed=False,production_confirmed=False)
    spec["process"]["hotwire"].update(wire_count="confirmar",effective_kerf_mm="confirmar",min_segment_mm="confirmar",min_radius_mm="confirmar")
    spec["process"]["feed"].update(xy_mm_min="confirmar",slow_curve_mm_min="confirmar")
    job=build_job(spec)
    output=ROOT/"outputs"/args.variant
    write_outputs(job,spec,output)
    print(output)
    return int(job.has_errors)
if __name__=="__main__":
    raise SystemExit(main())
