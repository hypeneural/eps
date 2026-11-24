"""Derive a contrast-safe palette from the supplied original logo; no remote assets."""
from PIL import Image
import colorsys

def luminance(rgb):
    vals=[v/255 for v in rgb]
    vals=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]
    return sum(a*b for a,b in zip(vals,(.2126,.7152,.0722)))

def palette(logo=None):
    primary=(21,88,117)
    if logo:
        with Image.open(logo) as im:
            im=im.convert("RGBA")
            im.thumbnail((160,160))
            counts={}
            pixels = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
            for r,g,b,a in pixels:
                h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255)
                if a>=200 and s>=.35 and .23<=v<=1:
                    key=tuple(min(255,(c//24)*24+12) for c in (r,g,b))
                    counts[key]=counts.get(key,0)+1
            if counts:
                primary=max(counts,key=counts.get)
    accent=primary
    while 1.05/(luminance(primary)+.05)<5:
        primary=tuple(int(v*.92) for v in primary)
    soft=tuple(round(v*.09+255*.91) for v in primary)
    return primary,soft,accent

def write_brand(path,logo=None):
    def hx(rgb): return "#%02x%02x%02x"%rgb
    primary,soft,accent=palette(logo)
    path.write_text(":root{--brand:"+hx(primary)+";--brand-soft:"+hx(soft)+";--accent:"+hx(accent)+"}\n",encoding="utf-8")
