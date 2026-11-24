"""Deterministic synthetic EPS bead texture."""
from random import Random
from PIL import Image, ImageDraw, ImageFilter

def eps_texture(size=512, seed=40):
    rng = Random(seed)
    image = Image.new("RGB", (size, size), (205,205,200))
    draw = ImageDraw.Draw(image)
    for y in range(-13,size+13,13):
        for x in range(-13,size+13,13):
            dx,dy=rng.randint(-3,3),rng.randint(-3,3)
            r=rng.randint(6,9)
            tone=rng.randint(221,249)
            box=(x+dx-r,y+dy-r,x+dx+r,y+dy+r)
            draw.ellipse(box,fill=(tone,tone,tone-2),outline=(194,195,192))
            draw.arc(box,195,285,fill=(252,252,250),width=1)
    return image.filter(ImageFilter.GaussianBlur(.35))
