"""Scale-consistent technical image for nominal review (not a CAM drawing)."""
from PIL import Image, ImageDraw

def write_section(roof,report,path):
    W,H=1800,600
    image=Image.new("RGB",(W,H),"white")
    d=ImageDraw.Draw(image)
    width,height=report["width_mm"],report["height_mm"]
    scale=min(1560/width,260/height)
    def p(x,y): return (120+x*scale,350-y*scale)
    d.polygon([p(x,y) for x,y in roof.core.exterior.coords],fill=(232,239,244),outline=(52,78,100),width=2)
    d.line([p(x,y) for x,y in report["profile_points_mm"]],fill=(26,101,155),width=3)
    x0,y0=p(0,0); x1,_=p(width,0)
    d.line([(x0,365),(x0,403)],fill="black")
    d.line([(x1,365),(x1,403)],fill="black")
    d.line([(x0,390),(x1,390)],fill="black")
    d.text(((x0+x1)/2-25,405),f"{width:g} mm",fill="black")
    d.text((120,45),"TP40 | SECAO NOMINAL - REVISAO, NAO CORTE",fill=(25,49,72))
    d.text((120,68),f"Altura {height:g} mm | EPS minimo {report['min_thickness_mm']:g} mm | Area {report['area_mm2']:g} mm2",fill="black")
    d.text((120,490),"Perfil em escala XY uniforme. Dimensoes fisicas e encaixe ainda nao homologados.",fill="black")
    image.save(path)
