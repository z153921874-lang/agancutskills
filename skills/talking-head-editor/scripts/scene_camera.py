"""Explicit 2D camera/object tracks for staged explanations. No inferred semantics."""
import math
from PIL import Image, ImageFilter, ImageOps


class Track:
    """Finite numeric keyframes; smooth/linear/hold applies from a key to the next."""
    def __init__(self, keys, fields):
        self.fields=tuple(fields)
        if not self.fields or not keys:raise ValueError('Nonempty fields and keys required')
        self.keys=[]
        for row in keys:
            if set(row)-set(self.fields)-{'time','ease'}:raise ValueError('Unknown track field')
            k={n:float(row[n]) for n in ('time',*self.fields)}
            if not all(math.isfinite(v) for v in k.values()):raise ValueError('Nonfinite track value')
            if k['time']<0 or (self.keys and k['time']<=self.keys[-1]['time']):raise ValueError('Times must increase')
            k['ease']=row.get('ease','smooth')
            if k['ease'] not in ('smooth','linear','hold'):raise ValueError('Unknown easing')
            self.keys.append(k)

    def at(self,t):
        if not math.isfinite(t):raise ValueError('Nonfinite time')
        if t<=self.keys[0]['time']:return {n:self.keys[0][n] for n in self.fields}
        if t>=self.keys[-1]['time']:return {n:self.keys[-1][n] for n in self.fields}
        for a,b in zip(self.keys,self.keys[1:]):
            if a['time']<=t<b['time']:
                p=(t-a['time'])/(b['time']-a['time'])
                if a['ease']=='smooth':p=p*p*(3-2*p)
                elif a['ease']=='hold':p=0
                return {n:a[n]+(b[n]-a[n])*p for n in self.fields}
        raise RuntimeError('Unreachable track interval')


class Camera:
    """Camera bounds have a fixed output aspect; overscan is rejected, not silently cropped."""
    def __init__(self,world_size,output_size,keys):
        self.world_size=tuple(world_size);self.output_size=tuple(output_size)
        for size in (self.world_size,self.output_size):
            if len(size)!=2 or any(not isinstance(v,int) or v<=0 for v in size):raise ValueError('Sizes must be positive integers')
        self.track=Track(keys,('x','y','width','height'))
        ratio=output_size[0]/output_size[1]
        for k in self.track.keys:
            x,y,w,h=(k[n] for n in ('x','y','width','height'))
            if w<1 or h<1 or x<0 or y<0 or x+w>world_size[0]+1e-6 or y+h>world_size[1]+1e-6:raise ValueError('Camera outside world')
            if not math.isclose(w/h,ratio,rel_tol=1e-6):raise ValueError('Camera aspect would distort content')

    def view(self,world,t):
        if world.size!=self.world_size:raise ValueError('World dimensions changed')
        r=self.track.at(t);x,y,w,h=(r[n] for n in ('x','y','width','height'))
        return world.resize(self.output_size,Image.Resampling.BICUBIC,box=(x,y,x+w,y+h))

    def project(self,point,t):
        r=self.track.at(t)
        return ((point[0]-r['x'])*self.output_size[0]/r['width'],(point[1]-r['y'])*self.output_size[1]/r['height'])


class AssetTrack:
    """Explicit source identity plus 2D rect, opacity and per-layer blur; clip outside canvas."""
    def __init__(self,asset_id,picture,keys,fit='contain'):
        if not isinstance(asset_id,str) or not asset_id:raise ValueError('Stable asset ID required')
        if fit not in ('contain','cover'):raise ValueError('Unknown fit')
        self.asset_id=asset_id;self.picture=picture.convert('RGBA');self.fit=fit
        self.track=Track(keys,('x','y','width','height','opacity','blur'))
        for k in self.track.keys:
            if k['width']<1 or k['height']<1 or not 0<=k['opacity']<=1 or not 0<=k['blur']<=64:raise ValueError('Invalid object state')

    def draw(self,canvas,t):
        if canvas.mode!='RGBA':raise ValueError('RGBA destination required')
        k=self.track.at(t)
        if k['opacity']<=0:return
        w,h=max(1,round(k['width'])),max(1,round(k['height']))
        src=self.picture
        if k['blur']>0:src=src.filter(ImageFilter.GaussianBlur(k['blur']))
        scaled=(ImageOps.contain if self.fit=='contain' else ImageOps.fit)(src,(w,h),Image.Resampling.LANCZOS)
        if k['opacity']<1:
            scaled.putalpha(scaled.getchannel('A').point(lambda a:round(a*k['opacity'])))
        x=round(k['x']+(w-scaled.width)/2);y=round(k['y']+(h-scaled.height)/2)
        canvas.alpha_composite(scaled,(x,y))
