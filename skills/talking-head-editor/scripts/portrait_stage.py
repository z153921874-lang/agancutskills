"""Place caller-cropped portrait frames or existing RGBA person mattes.

No segmentation, face detection, identity selection, or automatic layout decisions.
"""
import math
from PIL import Image,ImageDraw,ImageFilter,ImageOps


def frame_geometry(source_size, box, *, crop=None, fit='contain', focal=(.5,.5)):
    """Return source pixels actually visible after fitting; no face detection."""
    if fit not in ('contain','cover'):raise ValueError('fit must be contain or cover')
    sw,sh=source_size
    a,b,c,d=crop or (0,0,sw,sh)
    if a<0 or b<0 or c>sw or d>sh or c<=a or d<=b:raise ValueError('invalid source crop')
    x1,y1,x2,y2=map(float,box);w=x2-x1;h=y2-y1
    if min(w,h)<=0:raise ValueError('invalid output box')
    if len(focal)!=2 or any(not math.isfinite(float(v)) or not 0<=v<=1 for v in focal):raise ValueError('invalid focal point')
    cw,ch=c-a,d-b
    scale=min(w/cw,h/ch) if fit=='contain' else max(w/cw,h/ch)
    if fit=='contain':
        nw,nh=cw*scale,ch*scale
        bounds=(x1+(w-nw)/2,y1+(h-nh)/2,x1+(w+nw)/2,y1+(h+nh)/2)
        visible=(a,b,c,d)
    else:
        vw,vh=w/scale,h/scale
        vx=a+(cw-vw)*focal[0];vy=b+(ch-vh)*focal[1]
        visible=(vx,vy,vx+vw,vy+vh);bounds=(x1,y1,x2,y2)
    return {'visible_source':visible,'content_box':bounds,'scale':scale,'fit':fit}


def draw_portrait(canvas, source, box, *, mode='frame', crop=None,
                  radius=16, border=1, border_color='#758073',
                  opacity=1, shadow=True, anchor='bottom', fit='contain',
                  focal=(.5,.5), protected=None):
    if mode not in ('frame','cutout'):raise ValueError('mode must be frame or cutout')
    if anchor not in ('center','bottom'):raise ValueError('invalid anchor')
    if not all(math.isfinite(float(v)) for v in (*box,opacity)):raise ValueError('non-finite placement')
    if not 0<=opacity<=1:raise ValueError('invalid opacity')
    x1,y1,x2,y2=map(round,box);w=x2-x1;h=y2-y1
    if min(w,h)<16:raise ValueError('portrait box is too small')
    pic=source
    if crop is not None:
        a,b,c,d=map(round,crop)
        if a<0 or b<0 or c>source.width or d>source.height or c<=a or d<=b:raise ValueError('crop is outside source')
        pic=pic.crop((a,b,c,d))
    if mode=='cutout':
        if pic.mode!='RGBA' or pic.getchannel('A').getextrema()[0]==255:
            raise ValueError('cutout requires an actual transparent RGBA source')
        pic=ImageOps.contain(pic,(w,h),Image.Resampling.LANCZOS)
        px=x1+(w-pic.width)//2;py=y2-pic.height if anchor=='bottom' else y1+(h-pic.height)//2
        stage=Image.new('RGBA',canvas.size)
        if shadow:
            mask=Image.new('L',canvas.size);mask.paste(pic.getchannel('A'),(px+3,py+5))
            sh=Image.new('RGBA',canvas.size,(0,0,0,0));sh.putalpha(mask.point(lambda a:round(a*.14)).filter(ImageFilter.GaussianBlur(7)))
            stage.alpha_composite(sh)
        stage.alpha_composite(pic,(px,py))
        bounds=(px,py,px+pic.width,py+pic.height)
    else:
        geo=frame_geometry(source.size,box,crop=crop,fit=fit,focal=focal)
        if protected is not None:
            a,b,c,d=geo['visible_source'];pa,pb,pc,pd=protected
            if pc<=pa or pd<=pb or pa<a-1e-6 or pb<b-1e-6 or pc>c+1e-6 or pd>d+1e-6:
                raise ValueError('fitting would crop protected source content')
        if fit=='contain':
            pic=ImageOps.contain(pic.convert('RGBA'),(w,h),Image.Resampling.LANCZOS)
            x1+=(w-pic.width)//2;y1+=(h-pic.height)//2;w,h=pic.size;x2=x1+w;y2=y1+h
        else:
            pic=ImageOps.fit(pic.convert('RGBA'),(w,h),Image.Resampling.LANCZOS,centering=focal)
        mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius,fill=255)
        pic.putalpha(mask)
        if border:
            ImageDraw.Draw(pic).rounded_rectangle((0,0,w-1,h-1),radius,outline=border_color,width=border)
        stage=Image.new('RGBA',canvas.size)
        if shadow:
            mask2=Image.new('L',canvas.size);mask2.paste(mask,(x1,y1+8))
            sh=Image.new('RGBA',canvas.size,(0,0,0,0));sh.putalpha(mask2.point(lambda a:round(a*.3)).filter(ImageFilter.GaussianBlur(11)))
            stage.alpha_composite(sh)
        stage.alpha_composite(pic,(x1,y1));bounds=(x1,y1,x2,y2)
    if opacity<1:stage.putalpha(stage.getchannel('A').point(lambda a:round(a*opacity)))
    canvas.alpha_composite(stage)
    return bounds
