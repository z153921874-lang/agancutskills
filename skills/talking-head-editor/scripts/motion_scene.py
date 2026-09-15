"""Render explicit concepts and timed relationships as an original silent motion scene."""
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from editor import keys, num, integer, ffmpeg_path, probe


def checked(spec):
    keys(spec,'title eyebrow footer duration theme nodes edges statements')
    spec=dict(spec)
    spec['duration']=num(spec.get('duration',8),2,60)
    spec['theme']=spec.get('theme','dark')
    if spec['theme'] not in ('dark','paper'):raise ValueError('Unknown theme')
    def short(value,limit):
        if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 for c in value):raise ValueError('Invalid/long text')
    for key,limit in [('title',22),('eyebrow',42),('footer',50)]:short(spec.get(key,''),limit)
    if not spec.get('title','').strip():raise ValueError('Title required')
    if not isinstance(spec.get('nodes'),list) or not 1<=len(spec['nodes'])<=6:raise ValueError('Need 1-6 nodes')
    ids=set()
    for n in spec['nodes']:
        keys(n,'id label detail icon x y w h at')
        if not isinstance(n.get('id'),str) or not n['id'] or n['id'] in ids:raise ValueError('Unique node id required')
        ids.add(n['id']);short(n.get('label',''),10);short(n.get('detail',''),16)
        if n.get('icon','person') not in ('person','clock','home'):raise ValueError('Unknown icon')
        w=integer(n['w'],220,1000);h=integer(n['h'],170,430)
        num(n['x'],30,1250-w);num(n['y'],190,630-h);num(n['at'],0,spec['duration']-1)
    for i,n in enumerate(spec['nodes']):
        for other in spec['nodes'][i+1:]:
            if max(n['x'],other['x'])<min(n['x']+n['w'],other['x']+other['w']) and max(n['y'],other['y'])<min(n['y']+n['h'],other['y']+other['h']):
                raise ValueError('Node boxes overlap; revise layout')
    for e in spec.get('edges',[]):
        keys(e,'from to start end label at')
        if e['from'] not in ids or e['to'] not in ids:raise ValueError('Unknown edge node')
        short(e.get('label',''),10)
        for point in ('start','end'):
            if len(e[point])!=2:raise ValueError('Point needs x,y')
            num(e[point][0],0,1280);num(e[point][1],180,650)
        num(e['at'],0,spec['duration']-1)
        nodes={n['id']:n for n in spec['nodes']}
        if e['at']<max(nodes[e['from']]['at'],nodes[e['to']]['at']):raise ValueError('Edge precedes its nodes')
    for st in spec.get('statements',[]):
        keys(st,'text x y at size');short(st['text'],22)
        num(st['x'],0,1280);num(st['y'],180,630);num(st['at'],0,spec['duration']-1);integer(st.get('size',36),22,100)
    return spec


def smooth(t):
    t=min(1,max(0,t));return t*t*(3-2*t)


@lru_cache(maxsize=64)
def get_font(font_path,size):
    return ImageFont.truetype(str(font_path),size)


def frame(spec,t,font_path):
    paper=spec['theme']=='paper'
    bg,grid,fg,muted,accent,card=('#EEEBDD','#E1DDCD','#182D32','#56686A','#367B71','#FCFAF0') if paper else ('#111C24','#1A2932','#EDF1E6','#A1B6B5','#CBE5A0','#21323B')
    im=Image.new('RGB',(1280,720),bg);d=ImageDraw.Draw(im)
    fonts={n:get_font(str(font_path),n) for n in (20,22,26,30,36,46,100)}
    for x in range(0,1280,64):d.line((x,0,x,720),fill=grid)
    for y in range(0,720,64):d.line((0,y,1280,y),fill=grid)
    d.text((64,32),spec.get('eyebrow',''),font=fonts[20],fill=muted)
    d.text((64,82),spec['title'],font=fonts[46],fill=fg)
    d.line((64,157,1216,157),fill=accent,width=2)
    for n in spec['nodes']:
        p=smooth((t-n['at'])/.55)
        if not p:continue
        layer=Image.new('RGBA',im.size);ld=ImageDraw.Draw(layer)
        x,y,w,h=n['x'],n['y']+round(24*(1-p)),n['w'],n['h']
        ld.rounded_rectangle((x,y,x+w,y+h),radius=16,fill=card,outline=accent,width=2)
        cx,cy=x+w/2,y+30;icon=n.get('icon','person')
        if icon=='person':
            ld.ellipse((cx-15,cy-18,cx+15,cy+12),fill=accent)
            ld.rounded_rectangle((cx-28,cy+20,cx+28,cy+69),radius=18,fill=accent)
        elif icon=='clock':
            ld.ellipse((cx-35,cy-18,cx+35,cy+52),outline=accent,width=5)
            ld.line((cx,cy-7,cx,cy+17,cx+20,cy+29),fill=accent,width=5)
        else:
            ld.polygon([(cx-43,cy+12),(cx,cy-22),(cx+43,cy+12)],fill=accent)
            ld.rectangle((cx-30,cy+12,cx+30,cy+58),outline=accent,width=5)
            ld.rectangle((cx-9,cy+30,cx+9,cy+58),fill=accent)
        ld.text((cx,y+h-69),n['label'],font=fonts[30],fill=fg,anchor='mm')
        ld.text((cx,y+h-30),n.get('detail',''),font=fonts[22],fill=muted,anchor='mm')
        layer.putalpha(layer.getchannel('A').point(lambda a:round(a*p)))
        im=Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB');d=ImageDraw.Draw(im)
    for e in spec.get('edges',[]):
        p=smooth((t-e['at'])/.75)
        if not p:continue
        a,b=e['start'],e['end'];end=(a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p)
        d.line((tuple(a),end),fill=accent,width=5)
        if p>.9:
            angle=math.atan2(b[1]-a[1],b[0]-a[0]);d.polygon([tuple(b)]+[(b[0]-17*math.cos(angle+s),b[1]-17*math.sin(angle+s)) for s in (-.5,.5)],fill=accent)
            d.text(((a[0]+b[0])/2,(a[1]+b[1])/2-24),e.get('label',''),font=fonts[22],fill=fg,anchor='mm')
    for st in spec.get('statements',[]):
        if t>=st['at']:
            size=st.get('size',36);font=fonts.get(size) or ImageFont.truetype(str(font_path),size)
            d.text((st['x'],st['y']),st['text'],font=font,fill=accent,anchor='mm')
    d.text((64,676),spec.get('footer',''),font=fonts[20],fill=muted)
    return im


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--font',default='C:/Windows/Fonts/msyh.ttc');ap.add_argument('--ffmpeg')
    a=ap.parse_args();out=Path(a.output)
    if out.suffix.lower()!='.mp4' or out.exists() or out.with_suffix('.scene.json').exists():raise ValueError('Use a new MP4 path')
    spec=checked(json.loads(Path(a.spec).read_text(encoding='utf-8-sig')))
    if not Path(a.font).is_file():raise ValueError('Font unavailable')
    for n in spec['nodes']:
        for field,size in [('label',30),('detail',22)]:
            if get_font(a.font,size).getlength(n.get(field,''))>n['w']-32:
                raise ValueError('Node text too wide; shorten copy or enlarge node')
    for st in spec.get('statements',[]):
        extent=get_font(a.font,st.get('size',36)).getlength(st['text'])/2
        if st['x']-extent<30 or st['x']+extent>1250:
            raise ValueError('Statement extends outside safe horizontal bounds')
    fps=25;frames=round(spec['duration']*fps);ff=ffmpeg_path(a.ffmpeg)
    out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ff,'-hide_banner','-loglevel','error','-n','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r',str(fps),'-i','-',
         '-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    log=out.with_suffix('.encode.log')
    with log.open('wb') as errors:
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=errors)
        try:
            for i in range(frames):proc.stdin.write(frame(spec,i/fps,a.font).tobytes())
            proc.stdin.close();code=proc.wait()
        except BaseException:
            proc.kill();proc.wait();raise
    if code:raise RuntimeError('Encoding failed; see '+str(log))
    info=probe(ff,out)
    if abs(info['duration']-frames/fps)>.08 or info['audio']:raise RuntimeError('Output check failed')
    out.with_suffix('.scene.json').write_text(json.dumps({'spec':spec,'duration':frames/fps,'silent':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'duration':frames/fps,'silent':True}))


if __name__=='__main__':main()
