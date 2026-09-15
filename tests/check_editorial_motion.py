from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills'/'talking-head-editor'/'scripts'))
import editorial_motion as m
tests=[]
def check(name,truth):
    assert truth,name;tests.append(name)
def rejected(name,fn):
    try:fn()
    except ValueError:tests.append(name);return
    raise AssertionError(name)
check('ease_clamps_and_settles',m.ease(-1)==0 and m.ease(2)==1 and m.ease(.5)==.5)
a=m.paper_surface((240,300));b=m.paper_surface((240,300))
check('paper_fixed_seed_no_flicker',a.tobytes()==b.tobytes())
check('dark_surface_distinct',a.tobytes()!=m.paper_surface((240,300),dark=True).tobytes())
photo=Image.new('RGB',(200,100),'#AA1010');d=ImageDraw.Draw(photo);d.rectangle((0,0,12,12),fill='#00FF00');d.rectangle((187,87,199,99),fill='#0000FF')
c=Image.new('RGBA',(400,400),'#FFFFFF');m.photo_card(c,photo,(200,200),(200,200),border=0)
n=np.array(c)
check('contain_keeps_original_aspect',tuple(n[120,200,:3])==(239,239,223) and n[180,200,0]>150)
check('contain_preserves_corner_marks',((n[:,:,1]>230)&(n[:,:,0]<20)).sum()>70 and ((n[:,:,2]>230)&(n[:,:,0]<20)).sum()>70)
c0=c.copy();m.photo_card(c,photo,(200,200),(200,100),opacity=0)
check('opacity_zero_leaves_canvas',c.tobytes()==c0.tobytes())
rot=Image.new('RGBA',(400,400),'#FFFFFF');m.photo_card(rot,photo,(200,200),(200,100),angle=6)
nr=np.array(rot);check('rotated_corners_preserved',((nr[:,:,1]>220)&(nr[:,:,0]<30)).sum()>60 and ((nr[:,:,2]>220)&(nr[:,:,0]<30)).sum()>60)
rejected('invalid_fit_rejected',lambda:m.photo_card(c,photo,(200,200),(200,100),fit='stretch'))
rejected('invalid_size_rejected',lambda:m.photo_card(c,photo,(200,200),(float('nan'),100)))
rejected('invalid_zoom_rejected',lambda:m.focus_window(photo,(100,50),.5))
check('unit_focus_identical',m.focus_window(photo,(100,50),1).tobytes()==photo.tobytes())
zoom=m.focus_window(photo,(199,99),2);check('edge_focus_clamped',zoom.size==photo.size and np.array(zoom)[-3,-3,2]>230)
counts=[]
for p in [0,.25,.5,1,2]:
    ci=Image.new('RGBA',(200,200),'white');m.growing_line(ci,[(20,20),(170,20),(170,170)],p,color='black',width=4,arrow=True)
    counts.append(int((np.array(ci)[:,:,:3].sum(2)<50).sum()))
check('line_progress_and_final_hold',counts[0]==0 and counts[1]<counts[2]<counts[3] and counts[3]==counts[4])

print(f'{len(tests)} checks passed')
