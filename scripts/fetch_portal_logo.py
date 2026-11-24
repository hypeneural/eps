"""Fetch the company-provided original logo once on the development PC."""
import argparse
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from PIL import Image
URL="https://isonunes.com.br/wp-content/uploads/2018/06/isonunes-logo-1.png"
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,default=Path("portal_local/logo-isonunes.png"))
    a=p.parse_args()
    with urlopen(URL,timeout=20) as response:
        data=response.read(4*1024*1024+1)
    if len(data)>4*1024*1024:
        raise ValueError("Logo too large")
    with Image.open(BytesIO(data)) as im:
        if im.width*im.height>10_000_000:
            raise ValueError("Logo too large")
        im=im.convert("RGBA")
        im.thumbnail((480,180),Image.Resampling.LANCZOS)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        im.save(a.output,"PNG",optimize=True)
    print(a.output.resolve())
if __name__=="__main__":
    main()
