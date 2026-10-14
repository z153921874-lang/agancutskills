"""Measured author/title/verse layout over a caller-supplied illustration."""
from PIL import Image,ImageDraw

def draw_poetry(canvas,*,author,title,lines,box,heading_font,verse_font,
                color='#F4EADB',muted='#CDBB9B',active=None):
    if not author.strip() or not title.strip() or not lines:raise ValueError('author, title and verse are required')
    x1,y1,x2,y2=box
    if x2<=x1 or y2<=y1:raise ValueError('invalid poetry box')
    if active is not None and not 0<=active<len(lines):raise ValueError('invalid active line')
    d=ImageDraw.Draw(canvas)
    h=heading_font.size*1.6;v=verse_font.size*1.5
    if h*2+v*len(lines)>y2-y1:raise ValueError('poetry needs a taller box or a smaller font')
    for s,ff in [(author,heading_font),(title,heading_font)]+[(s,verse_font) for s in lines]:
        if d.textlength(s,font=ff)>x2-x1:raise ValueError('poetry would overflow; reflow or reduce font size')
    d.text((x1,y1),author,font=heading_font,fill=muted)
    d.text((x1,y1+h),title,font=heading_font,fill=color)
    y=y1+h*2
    bounds=[]
    for i,s in enumerate(lines):
        fill=color if active is None or i==active else muted
        d.text((x1,y),s,font=verse_font,fill=fill)
        bounds.append((x1,y,x1+d.textlength(s,font=verse_font),y+v));y+=v
    return bounds
