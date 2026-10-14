"""Caller-supplied photographic plates and restrained editorial surfaces.

No asset generation/retrieval, automatic face avoidance, perspective, or audio.
"""
from dataclasses import dataclass
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


@dataclass
class Plate:
    asset_id: str
    image: Image.Image
    content_box: tuple


def surface(size, dark=False, grid=False, seed=17):
    w,h=map(int,size)
    if min(w,h)<16:raise ValueError('surface is too small')
    yy,xx=np.mgrid[:h,:w]
    v=((xx-w*.47)/w)**2+((yy-h*.42)/h)**2
    base=np.array([27,31,30] if dark else [239,235,221],float)
    pixels=base-v[...,None]*(27 if dark else 38)
    pixels+=np.random.default_rng(seed).normal(0,.7,(h,w,1))
    im=Image.fromarray(np.uint8(np.clip(pixels,0,255))).convert('RGBA')
    if grid:
        layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer)
        color=(172,181,167,10) if dark else (91,100,83,16)
        for x in range(0,w,60):d.line((x,0,x,h),fill=color)
        for y in range(0,h,60):d.line((0,y,w,y),fill=color)
        im.alpha_composite(layer)
    return im


def make_plate(asset_id, picture, size, *, fit='contain', header=None,
               header_font=None, border=7, radius=0, dark=False):
    if not asset_id:raise ValueError('asset_id is required')
    w,h=map(int,size)
    if min(w,h)<16 or not 0<=border<min(w,h)/4:raise ValueError('invalid plate dimensions')
    if fit not in ('contain','cover'):raise ValueError('fit must be contain or cover')
    bar=30 if header else 0
    if header and header_font is None:raise ValueError('header_font is required for a header')
    cw,ch=w-2*border,h-2*border-bar
    if ch<8:raise ValueError('header leaves no content')
    panel=Image.new('RGBA',(w,h),'#1B201E' if dark else '#ECE8DB')
    inner=ImageOps.contain(picture.convert('RGBA'),(cw,ch),Image.Resampling.LANCZOS) if fit=='contain' else ImageOps.fit(picture.convert('RGBA'),(cw,ch),Image.Resampling.LANCZOS)
    x=border+(cw-inner.width)//2;y=border+bar+(ch-inner.height)//2
    panel.alpha_composite(inner,(x,y))
    d=ImageDraw.Draw(panel);d.rectangle((0,0,w-1,h-1),outline='#5A625B' if dark else '#9D9C8E',width=1)
    if header:
        d.rectangle((1,1,w-2,bar+border-1),fill='#302E26' if dark else '#D8CCAF')
        d.text((border+5,4),header,font=header_font,fill='#EDE9DE' if dark else '#34382F')
        for xx in (w-39,w-24):d.rectangle((xx,12,xx+5,17),outline='#7C786B',width=1)
    if radius:
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius,fill=255)
        panel.putalpha(mask)
    return Plate(asset_id,panel,(x,y,x+inner.width,y+inner.height))


def draw_plate(canvas, plate, center, *, angle=0, opacity=1, blur=0, shadow=True):
    if not all(math.isfinite(float(x)) for x in (*center,angle,opacity,blur)):raise ValueError('non-finite transform')
    if not 0<=opacity<=1 or blur<0:raise ValueError('invalid opacity or blur')
    pic=plate.image.rotate(angle,Image.Resampling.BICUBIC,expand=True) if angle else plate.image.copy()
    if blur:pic=pic.filter(ImageFilter.GaussianBlur(blur))
    margin=26 if shadow else 0
    out=Image.new('RGBA',(pic.width+2*margin,pic.height+2*margin))
    if shadow:
        alpha=Image.new('L',out.size);alpha.paste(pic.getchannel('A'),(margin,margin+7))
        sh=Image.new('RGBA',out.size,(0,0,0,0));sh.putalpha(alpha.point(lambda a:round(a*.29)).filter(ImageFilter.GaussianBlur(9)))
        out.alpha_composite(sh)
    out.alpha_composite(pic,(margin,margin))
    if opacity<1:out.putalpha(out.getchannel('A').point(lambda a:round(a*opacity)))
    x=round(center[0]-out.width/2);y=round(center[1]-out.height/2)
    canvas.alpha_composite(out,(x,y))
    return (x+margin,y+margin,x+margin+pic.width,y+margin+pic.height)


def overlap_fraction(moving_box, protected_box):
    x1,y1,x2,y2=moving_box;a1,b1,a2,b2=protected_box
    if x2<=x1 or y2<=y1 or a2<=a1 or b2<=b1:raise ValueError('empty rectangle')
    area=max(0,min(x2,a2)-max(x1,a1))*max(0,min(y2,b2)-max(y1,b1))
    return area/((a2-a1)*(b2-b1))
