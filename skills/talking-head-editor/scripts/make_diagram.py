"""Generate progressive comparison, branching or cycle cards from explicit copy."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create(spec, output, font_path):
    kind=spec.get('kind')
    if kind not in ('compare','branch','cycle'):
        raise ValueError('kind must be compare, branch or cycle')
    allowed={'kind','title','nodes','center','footer'}
    if set(spec)-allowed:raise ValueError('Unknown fields: '+str(set(spec)-allowed))
    nodes=spec.get('nodes',[])
    if not isinstance(nodes,list):raise ValueError('nodes must be a list')
    expected=2 if kind=='compare' else 3
    if len(nodes)!=expected:raise ValueError(f'{kind} requires {expected} nodes')
    for value,limit in [(spec.get('title'),24),(spec.get('footer',''),52)]+[(n,26) for n in nodes]:
        if not isinstance(value,str) or len(value)>limit or any(ord(c)<32 for c in value):
            raise ValueError('Text must be a short string without control characters')
    if not spec['title'].strip() or any(not n.strip() for n in nodes):raise ValueError('Empty title/node')
    if kind=='branch' and (not isinstance(spec.get('center'),str) or not 1<=len(spec['center'])<=14 or not spec['center'].strip() or any(ord(c)<32 for c in spec['center'])):
        raise ValueError('branch needs center text, 1-14 characters')
    if not Path(font_path).is_file():raise ValueError('Font missing; supply --font')
    out=Path(output)
    if out.exists():raise ValueError('Output directory exists; choose a new one')
    out.mkdir(parents=True)
    W,H=1920,1080
    fonts={n:ImageFont.truetype(str(font_path),n) for n in (26,38,44,66)}
    bg='#101B26';accent='#92E5BF';fg='#F1F5F7';muted='#A7BAC7'
    def text(draw,xy,value,size=44,color=fg,max_width=650):
        lines=[];current=''
        for char in value:
            if draw.textlength(current+char,font=fonts[size])>max_width and current:
                lines.append(current);current=''
            current+=char
        lines.append(current)
        if len(lines)>3:raise ValueError('Text does not fit; shorten copy')
        x,y=xy;line_h=size*1.4
        for j,line in enumerate(lines):
            draw.text((x,y+(j-(len(lines)-1)/2)*line_h),line,font=fonts[size],fill=color,anchor='mm')
    def box(draw,rect,label):
        draw.rounded_rectangle(rect,radius=24,fill='#203343',outline=accent,width=3)
        text(draw,((rect[0]+rect[2])/2,(rect[1]+rect[3])/2),label,max_width=rect[2]-rect[0]-60)
    def arrow(draw,start,end):
        draw.line((start,end),fill=accent,width=6)
        angle=math.atan2(end[1]-start[1],end[0]-start[0]);length=22
        points=[end]+[(end[0]-length*math.cos(angle+a),end[1]-length*math.sin(angle+a)) for a in (-.5,.5)]
        draw.polygon(points,fill=accent)
    files=[]
    for count in range(1,expected+1):
        im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
        for x in range(0,W,80):d.line((x,0,x,H),fill='#162632',width=1)
        for y in range(0,H,80):d.line((0,y,W,y),fill='#162632',width=1)
        text(d,(960,130),spec['title'],66,max_width=1740)
        d.line((120,230,1800,230),fill='#385461',width=2)
        if kind=='compare':
            for i,n in enumerate(nodes[:count]):
                x=140+i*870
                box(d,(x,360,x+750,760),n)
            if count==2:text(d,(960,560),'VS',38,accent,100)
        elif kind=='branch':
            box(d,(140,445,690,665),spec['center'])
            for i,n in enumerate(nodes[:count]):
                y=320+i*225
                arrow(d,(710,555),(1130,y+80));box(d,(1150,y,1770,y+160),n)
        else:
            centers=[(960,370),(1440,760),(480,760)]
            rects=[(x-290,y-95,x+290,y+95) for x,y in centers]
            for i in range(count):box(d,rects[i],nodes[i])
            for i in range(count-1+(count==3)):
                a,b=centers[i%3],centers[(i+1)%3]
                dx,dy=b[0]-a[0],b[1]-a[1]
                # Exit each rectangle before drawing the directed connection.
                f=min(310/abs(dx) if dx else 99,115/abs(dy) if dy else 99)
                arrow(d,(a[0]+dx*f,a[1]+dy*f),(b[0]-dx*f,b[1]-dy*f))
        if spec.get('footer'):text(d,(960,1000),spec['footer'],26,muted,1720)
        name=f'stage-{count:02}.png';im.save(out/name);files.append(name)
    (out/'diagram.json').write_text(json.dumps({'spec':spec,'size':[W,H],'stages':files,
        'note':'Illustration from supplied copy; not verified evidence. Stage timing must follow speech.'},ensure_ascii=False,indent=2),encoding='utf-8')
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True);p.add_argument('--output-dir',required=True)
    p.add_argument('--font',default='C:/Windows/Fonts/msyh.ttc')
    a=p.parse_args();spec=json.loads(Path(a.spec).read_text(encoding='utf-8-sig'))
    print(json.dumps(create(spec,a.output_dir,a.font)))


if __name__=='__main__':main()
