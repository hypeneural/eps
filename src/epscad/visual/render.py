"""CPU-only illustrative product preview."""
from PIL import Image, ImageDraw, ImageEnhance
from shapely.geometry.polygon import orient
from epscad.visual.materials import eps_texture

def render_roof(roof,path,*,assembly=False,status="draft"):
    W,H=1600,1000
    xmin,ymin,xmax,ymax=roof.core.bounds
    w,h,depth=xmax-xmin,ymax-ymin,roof.length_mm
    scale=min(1320/(w+depth*.40),710/(h+depth*.38))
    def p(x,y,z):
        return (int(110+(x-xmin+z*.40)*scale),int(790-(y-ymin+z*.38)*scale))
    img=Image.new("RGB",(W,H),(238,242,246))
    ImageDraw.Draw(img).ellipse((70,745,1450,865),fill=(219,225,230))
    tile=eps_texture().resize((256,256))
    surface=Image.new("RGB",(W,H))
    for x in range(0,W,256):
        for y in range(0,H,256):
            surface.paste(tile,(x,y))
    def face(poly,shade,textured):
        mask=Image.new("L",(W,H),0)
        ImageDraw.Draw(mask).polygon(poly,fill=255)
        layer=ImageEnhance.Brightness(surface).enhance(shade) if textured else Image.new("RGB",(W,H),tuple(int(c*shade) for c in (155,166,177)))
        img.paste(layer,(0,0),mask)
        ImageDraw.Draw(img).line(poly+[poly[0]],fill=(145,151,157),width=1)
    def part(shape,textured,shift=0):
        ring=list(orient(shape,sign=1).exterior.coords)[:-1]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            nx,ny=b[1]-a[1],a[0]-b[0]
            if nx*.40+ny*.38 > 0:
                face([p(a[0],a[1]+shift,0),p(b[0],b[1]+shift,0),p(b[0],b[1]+shift,depth),p(a[0],a[1]+shift,depth)],.99 if abs(ny)>abs(nx) else .80,textured)
        face([p(x,y+shift,0) for x,y in ring],.88,textured)
    if assembly:
        part(roof.metal,False,-max(8,h*.16))
    part(roof.core,True)
    d=ImageDraw.Draw(img)
    d.text((80,55),"TP40 | EPS + METAL (VISTA EXPLODIDA)" if assembly else "TP40 | NUCLEO EPS",fill=(33,48,63))
    d.text((80,82),f"{w:g} x {h:g} x {depth:g} mm | {status.upper()} | visual nominal",fill=(52,67,83))
    d.text((80,930),"Textura ilustrativa. Metal simplificado; nao usar imagem como medida ou arquivo de corte.",fill=(52,67,83))
    img.save(path)
