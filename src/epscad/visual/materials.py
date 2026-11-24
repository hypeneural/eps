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

def eps_normal(size=512):
    """Approximate tangent-space normal map from the procedural bead relief."""
    import numpy as np
    height=np.asarray(eps_texture(size).convert("L"),dtype=np.float32)/255.0
    gy,gx=np.gradient(height)
    normals=np.stack((-gx*3,gy*3,np.ones_like(height)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    return Image.fromarray(np.uint8(np.clip((normals*.5+.5)*255,0,255)))
