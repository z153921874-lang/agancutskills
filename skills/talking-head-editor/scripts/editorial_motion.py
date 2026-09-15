"""Small Pillow compositing primitives for staged photographic explanation boards.

Images are caller supplied; no asset retrieval, subject segmentation or 3D inference.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

def ease(value):
    value=max(0.,min(1.,float(value)))
    return value*value*(3-2*value)

def paper_surface(size=(720,1280),dark=False,seed=73):
    w,h=size;rng=np.random.default_rng(seed)
    y,x=np.mgrid[:h,:w];v=((x-w/2)/w)**2+((y-h/2)/h)**2
    base=np.array([23,28,27] if dark else [236,235,220],dtype=float)
    a=base[None,None,:]-v[:,:,None]*(18 if dark else 33)
    a=a+rng.normal(0,.85,(h,w,1))
    im=Image.fromarray(np.uint8(np.clip(a,0,255))).convert('RGBA')
    grid=Image.new('RGBA',size);d=ImageDraw.Draw(grid)
    color=(170,200,176,12) if dark else (76,92,77,20)
    for xx in range(0,w,48):d.line((xx,0,xx,h),fill=color,width=1)
    for yy in range(0,h,48):d.line((0,yy,w,yy),fill=color,width=1)
    im.alpha_composite(grid)
    return im

def photo_card(canvas,picture,center,size,angle=0,opacity=1,border=9,fit='contain'):
    """Preserve aspect ratio; padded frame and shadow rotate together.

    Size is the unrotated inner image area. Rotation expands the final bounds.
    """
    if any(not math.isfinite(n) or n<4 for n in size):raise ValueError('size must be finite and >= 4')
    w,h=map(round,size)
    if fit not in ('contain','cover'):raise ValueError('fit must be contain or cover')
    if not math.isfinite(angle):raise ValueError('angle must be finite')
    if not isinstance(border,int) or border<0:raise ValueError('border must be a nonnegative integer')
    if not 0<=opacity<=1:raise ValueError('opacity must be between 0 and 1')
    card=Image.new('RGBA',(w+border*2,h+border*2),'#EFEFDF')
    src=picture.convert('RGBA')
    inner=ImageOps.contain(src,(w,h),Image.Resampling.LANCZOS) if fit=='contain' else ImageOps.fit(src,(w,h),Image.Resampling.LANCZOS)
    card.alpha_composite(inner,(border+(w-inner.width)//2,border+(h-inner.height)//2))
    card=card.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    padded=Image.new('RGBA',(card.width+48,card.height+48))
    alpha=Image.new('L',padded.size);alpha.paste(card.getchannel('A'),(24,30))
    shadow=Image.new('RGBA',padded.size,(0,0,0,0));shadow.putalpha(alpha.point(lambda x:round(x*.25)).filter(ImageFilter.GaussianBlur(10)))
    padded.alpha_composite(shadow);padded.alpha_composite(card,(24,24))
    if opacity<1:padded.putalpha(padded.getchannel('A').point(lambda x:round(x*opacity)))
    canvas.alpha_composite(padded,(round(center[0]-padded.width/2),round(center[1]-padded.height/2)))

def growing_line(canvas,points,progress,color='#718168',width=3,arrow=False):
    """Draw a polyline progressively by arc length, without moving completed points."""
    p=max(0.,min(1.,float(progress)))
    if p<=0 or len(points)<2:return
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    remain=sum(lengths)*p;draw=ImageDraw.Draw(canvas);last=None;angle=0
    for a,b,length in zip(points,points[1:],lengths):
        fraction=min(1,remain/max(length,1e-9));end=(a[0]+(b[0]-a[0])*fraction,a[1]+(b[1]-a[1])*fraction)
        draw.line([a,end],fill=color,width=width);last=end;angle=math.atan2(b[1]-a[1],b[0]-a[0]);remain-=length
        if remain<=0:break
    if arrow and p>=1 and last:
        draw.line([(last[0]-13*math.cos(angle-.5),last[1]-13*math.sin(angle-.5)),last,(last[0]-13*math.cos(angle+.5),last[1]-13*math.sin(angle+.5))],fill=color,width=width)

def focus_window(picture,center,scale=1):
    """2D crop to a named image detail. Caller retains captions outside this transform."""
    w,h=picture.size
    if not math.isfinite(scale) or scale<1:raise ValueError('scale must be finite and >= 1')
    if any(not math.isfinite(v) for v in center):raise ValueError('center must be finite')
    ww,hh=w/scale,h/scale
    x=min(w-ww,max(0,center[0]-ww/2));y=min(h-hh,max(0,center[1]-hh/2))
    return picture.crop((round(x),round(y),round(x+ww),round(y+hh))).resize((w,h),Image.Resampling.BICUBIC)
