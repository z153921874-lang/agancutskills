"""Local v2 renderer: deterministic plans, no arbitrary filter/ASS execution from JSON."""
import copy
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

VERSION = '2.7'


def ffmpeg_path(explicit=None):
    if explicit:
        return str(Path(explicit).resolve())
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise ValueError('FFmpeg missing: pass --ffmpeg; no automatic installation.')


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(p.stderr[-6000:])
    return p


def probe(ff, path):
    p = subprocess.run([ff, '-hide_banner', '-i', str(path)], capture_output=True,
                       encoding='utf-8', errors='replace')
    text = p.stderr
    dm = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
    line = next((x for x in text.splitlines() if re.search(r'Stream .*Video:', x)), '')
    vm = re.search(r'[, ](\d{2,5})x(\d{2,5})(?:[, ])', line)
    if not vm and not re.search(r'Stream .*Audio:', text):
        raise ValueError(f'Cannot inspect media: {path}')
    return {'duration': int(dm[1])*3600+int(dm[2])*60+float(dm[3]) if dm else None,
            'width': int(vm[1]) if vm else None, 'height': int(vm[2]) if vm else None,
            'video': bool(vm), 'audio': bool(re.search(r'Stream .*Audio:', text))}


def num(x, lo=0, hi=1e9):
    if isinstance(x, bool):
        raise ValueError('Boolean is not a numeric value')
    x = float(x)
    if not math.isfinite(x) or not lo <= x <= hi:
        raise ValueError(f'Out of range: {x}, expected {lo}..{hi}')
    return x


def integer(x, lo, hi):
    x = num(x, lo, hi)
    if x != int(x):
        raise ValueError('Expected integer')
    return int(x)


def color(x):
    if not isinstance(x, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', x):
        raise ValueError('Color must be #RRGGBB')
    return x


def keys(obj, allowed):
    extra = set(obj) - set(allowed.split())
    if extra:
        raise ValueError('Unknown plan fields: ' + ', '.join(sorted(extra)))


def fade(obj, duration):
    for key in ('fade_in', 'fade_out'):
        obj[key] = num(obj.get(key, 0), 0, duration)
    if obj['fade_in'] + obj['fade_out'] > duration + 1e-7:
        raise ValueError('Fades overlap beyond duration')


def validate(raw, base, ff):
    p = copy.deepcopy(raw)
    keys(p, 'version width height fps font clips texts audio effects overlays')
    if p.get('version', 2) not in (1, 2, '2.0'):
        raise ValueError('Unsupported plan version')
    p['width'], p['height'] = [integer(p.get(k, d), 64, 4096) for k,d in [('width',1080),('height',1920)]]
    w,h = p['width'], p['height']
    if w%2 or h%2:
        raise ValueError('Output dimensions must be even')
    p['fps'] = num(p.get('fps',30),1,60)
    fps = p['fps']
    p['font'] = str(p.get('font','Microsoft YaHei'))
    if any(c in p['font'] for c in ',\r\n{}\\'):
        raise ValueError('Invalid font name')
    cache, warnings, mapping = {}, [], []

    def media(o, kind, still=False):
        src = (base / o['source']).resolve()
        if not src.is_file():
            raise ValueError(f'Missing media: {src}')
        if src not in cache:
            cache[src] = probe(ff,src)
        info = cache[src]
        if not info[kind]:
            raise ValueError(f'Media has no {kind}: {src}')
        o['source'] = str(src)
        if not still and info['duration'] is None:
            raise ValueError('Media duration is unknown')
        return info

    def window(o):
        o['start'],o['end'] = num(o['start']),num(o['end'])
        if o['end'] <= o['start'] or o['end'] > total+1e-7:
            raise ValueError('Effect/text outside output timeline')
        return o['end']-o['start']

    total = 0
    if not p.get('clips'):
        raise ValueError('At least one clip is required')
    for c in p['clips']:
        keys(c,'source start end zoom zoom_end focus_x focus_y focus_x_end focus_y_end gain fade_in fade_out')
        info = media(c,'video')
        c['start'],c['end'] = num(c['start']),num(c['end'])
        if c['end'] <= c['start'] or c['end'] > info['duration']+.03:
            raise ValueError('Invalid source clip interval')
        frames = round((c['end']-c['start'])*fps)
        if frames < 1:
            raise ValueError('Clip is shorter than an output frame')
        duration = frames/fps
        if abs(duration-(c['end']-c['start'])) > .00001:
            warnings.append('Clip length rounded to frame grid; use returned source map for text alignment.')
        c['_frames'],c['_duration'],c['_audio'] = frames,duration,info['audio']
        c['zoom'] = num(c.get('zoom',1),1,3)
        c['zoom_end'] = num(c.get('zoom_end',c['zoom']),1,3)
        for k in ('focus_x','focus_y'):
            c[k] = num(c.get(k,.5),0,1)
            c[k+'_end'] = num(c.get(k+'_end',c[k]),0,1)
        c['gain'] = num(c.get('gain',1),0,4)
        fade(c,duration)
        if not info['audio']:
            warnings.append('Source has no audio; silent samples will be inserted: '+str(c['source']))
        mapping.append({'source':c['source'],'source_start':c['start'],
                        'source_end':c['end'],'output_start':total,'output_end':total+duration})
        total += duration
    for t in p.setdefault('texts',[]):
        keys(t,'start end text kind size color x y rotation rotation_end fade_in fade_out pop slide_from animation_duration keyframes layer outline outline_color')
        duration = window(t)
        if t.get('kind','caption') not in ('caption','emphasis'):
            raise ValueError('Unknown text kind')
        t['kind'] = t.get('kind','caption')
        t['layer']=t.get('layer','front')
        if t['layer'] not in ('front','behind'):
            raise ValueError('Text layer must be front or behind')
        if not isinstance(t['text'],str) or not t['text'].strip():
            raise ValueError('Text is empty')
        t['size'] = num(t.get('size',48),8,500)
        t['color'] = color(t.get('color','#FFFFFF'))
        t['outline'] = num(t.get('outline',2),0,10)
        t['outline_color'] = color(t.get('outline_color','#000000'))
        t['x'],t['y'] = num(t.get('x',w/2),0,w),num(t.get('y',h*.15 if t['kind']=='emphasis' else h*.88),0,h)
        t['rotation'] = num(t.get('rotation',0),-180,180)
        t['rotation_end']=num(t.get('rotation_end',t['rotation']),-180,180)
        fade(t,duration)
        t['animation_duration'] = num(t.get('animation_duration',min(.3,duration)),.001,duration)
        if not isinstance(t.get('pop',False),bool):
            raise ValueError('pop must be boolean')
        if 'slide_from' in t:
            if len(t['slide_from']) != 2:
                raise ValueError('slide_from must be [x,y]')
            t['slide_from'] = [num(t['slide_from'][0],-w,2*w),num(t['slide_from'][1],-h,2*h)]
        if 'keyframes' in t:
            if any((t.get('pop'),t.get('slide_from'),t['fade_in'],t['fade_out'],t['rotation']!=t['rotation_end'])):
                raise ValueError('Tracked text keyframes cannot combine with entry animations in v2')
            last = -1
            for k in t['keyframes']:
                keys(k,'time x y')
                k['time'] = num(k['time'],0,duration)
                k['x'],k['y'] = num(k['x'],0,w),num(k['y'],0,h)
                if k['time'] <= last:
                    raise ValueError('Keyframes must be strictly ordered')
                last = k['time']
            if len(t['keyframes'])<2 or t['keyframes'][0]['time']!=0 or abs(last-duration)>.001:
                raise ValueError('Keyframes must span the complete text duration')
    for e in p.setdefault('effects',[]):
        keys(e,'type start end sigma x y x_end y_end radius_x radius_y dim feather')
        window(e)
        if e['type']=='blur':
            e['sigma'] = num(e.get('sigma',12),.1,60)
        elif e['type']=='spotlight':
            for k,extent in [('x',w),('y',h)]:
                e[k]=num(e[k],0,extent)
                e[k+'_end']=num(e.get(k+'_end',e[k]),0,extent)
            e['radius_x']=num(e.get('radius_x',w*.15),5,w)
            e['radius_y']=num(e.get('radius_y',h*.15),5,h)
            e['dim']=num(e.get('dim',.65),0,1)
            e['feather']=num(e.get('feather',.18),.01,2)
        else:
            raise ValueError('Unknown effect type')
    for o in p.setdefault('overlays',[]):
        keys(o,'source source_start still start end x y x_end y_end width height crop opacity border border_color corner_radius fade_in fade_out fit pad_color easing move_duration rotation rotation_end')
        duration=window(o)
        o['still']=o.get('still',Path(o['source']).suffix.lower() in ('.png','.jpg','.jpeg','.webp'))
        if not isinstance(o['still'],bool):
            raise ValueError('still must be boolean')
        info=media(o,'video',still=o['still'])
        o['source_start']=num(o.get('source_start',0))
        if not o['still'] and o['source_start']+duration > info['duration']+.03:
            raise ValueError('Overlay exceeds source duration')
        o['width'],o['height']=integer(o['width'],2,w),integer(o['height'],2,h)
        for k,extent,size in [('x',w,o['width']),('y',h,o['height'])]:
            o[k]=num(o[k],0,extent-size)
            o[k+'_end']=num(o.get(k+'_end',o[k]),0,extent-size)
        if 'crop' in o:
            if len(o['crop'])!=4:
                raise ValueError('crop must be [x,y,width,height] in source pixels')
            x,y,cw,ch=[integer(x,0,100000) for x in o['crop']]
            if cw<2 or ch<2 or x+cw>info['width'] or y+ch>info['height']:
                raise ValueError('Overlay crop exceeds source bounds')
            o['crop']=[x,y,cw,ch]
        o['rotation']=num(o.get('rotation',0),-20,20)
        o['rotation_end']=num(o.get('rotation_end',o['rotation']),-20,20)
        o['fit']=o.get('fit','cover')
        if o['fit'] not in ('cover','contain'):raise ValueError('fit must be cover or contain')
        o['pad_color']=color(o.get('pad_color','#101B26'))
        o['easing']=o.get('easing','linear')
        if o['easing'] not in ('linear','smooth'):raise ValueError('Unknown easing')
        o['move_duration']=num(o.get('move_duration',duration),.001,duration)
        o['opacity']=num(o.get('opacity',1),0,1)
        o['border']=integer(o.get('border',0),0,min(o['width'],o['height'])//4)
        o['border_color']=color(o.get('border_color','#FFFFFF'))
        o['corner_radius']=num(o.get('corner_radius',0),0,min(o['width'],o['height'])/2)
        fade(o,duration)
    for a in p.setdefault('audio',[]):
        keys(a,'source source_start start duration gain fade_in fade_out duck')
        info=media(a,'audio')
        a['source_start']=num(a.get('source_start',0))
        a['start']=num(a['start'],0,total)
        a['duration']=num(a['duration'],.001,total)
        if a['start']+a['duration']>total+.0001 or a['source_start']+a['duration']>info['duration']+.03:
            raise ValueError('External audio exceeds source or timeline')
        a['gain']=num(a.get('gain',.15),0,4)
        if not isinstance(a.get('duck',False),bool):
            raise ValueError('duck must be boolean')
        a['duck']=a.get('duck',False)
        fade(a,a['duration'])
    return p,total,mapping,list(dict.fromkeys(warnings))


def stamp(t,srt=False):
    unit=1000 if srt else 100
    sec,frac=divmod(round(t*unit),unit)
    minute,sec=divmod(sec,60)
    hour,minute=divmod(minute,60)
    return f'{hour:02}:{minute:02}:{sec:02},{frac:03}' if srt else f'{hour}:{minute:02}:{sec:02}.{frac:02}'


def write_text(p,folder):
    w,h=p['width'],p['height']
    ass=(f'[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\n'
         '[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n'
         f'Style: Default,{p["font"]},48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,5,30,30,30,1\n'
         '[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n')
    subs={'caption':[],'emphasis':[]}
    buffers={'front':ass,'behind':ass}
    for t in sorted(p['texts'],key=lambda t:t['start']):
        raw=t['text'].replace('\r','')
        safe=raw.replace('\\','＼').replace('{','｛').replace('}','｝').replace('\n',r'\N')
        c=t['color'][1:]
        tags=f'\\an5\\fs{t["size"]}\\c&H{c[4:6]}{c[2:4]}{c[:2]}&\\frz{t["rotation"]}'
        oc=t['outline_color'][1:]
        tags+=f'\\bord{t["outline"]}\\3c&H{oc[4:6]}{oc[2:4]}{oc[:2]}&'
        if t['kind']=='emphasis':
            tags+='\\b1'
        if 'keyframes' in t:
            events=[]
            for left,right in zip(t['keyframes'],t['keyframes'][1:]):
                pos=f'\\move({left["x"]},{left["y"]},{right["x"]},{right["y"]})'
                events.append((t['start']+left['time'],t['start']+right['time'],tags+pos))
        else:
            ms=round(t['animation_duration']*1000)
            if 'slide_from' in t:
                x,y=t['slide_from']
                tags+=f'\\move({x},{y},{t["x"]},{t["y"]},0,{ms})'
            else:
                tags+=f'\\pos({t["x"]},{t["y"]})'
            if t.get('pop'):
                tags+=f'\\fscx75\\fscy75\\t(0,{round(ms*.6)},\\fscx112\\fscy112)\\t({round(ms*.6)},{ms},\\fscx100\\fscy100)'
            tags+=f'\\fad({round(t["fade_in"]*1000)},{round(t["fade_out"]*1000)})'
            if t['rotation']!=t['rotation_end']:
                tags+=f'\\t(0,{round((t["end"]-t["start"])*1000)},\\frz{t["rotation_end"]})'
            events=[(t['start'],t['end'],tags)]
        for start,end,tags in events:
            buffers[t['layer']]+=f'Dialogue: 0,{stamp(start)},{stamp(end)},Default,,0,0,0,,{{{tags}}}{safe}\n'
        blocks=subs[t['kind']]
        blocks.append(f'{len(blocks)+1}\n{stamp(t["start"],True)} --> {stamp(t["end"],True)}\n{raw}\n')
    (folder/'text.ass').write_text(buffers['front'],encoding='utf-8-sig')
    (folder/'behind.ass').write_text(buffers['behind'],encoding='utf-8-sig')
    for kind,blocks in subs.items():
        if blocks:
            (folder/(kind+'.srt')).write_text('\n'.join(blocks),encoding='utf-8-sig')


def afades(a,duration):
    result=[]
    if a['fade_in']:
        result.append(f'afade=t=in:st=0:d={a["fade_in"]}')
    if a['fade_out']:
        result.append(f'afade=t=out:st={duration-a["fade_out"]}:d={a["fade_out"]}')
    return result


def motion(a,b,start,end,variable='t',easing='linear'):
    if a==b:
        return str(a)
    u=f'clip(({variable}-{start})/{end-start},0,1)'
    if easing=='smooth':u=f'({u}*{u}*(3-2*{u}))'
    return f'({a}+({b-a})*{u})'


def graph(p,total,ff):
    w,h,fps=p['width'],p['height'],p['fps']
    cmd=[ff,'-hide_banner','-loglevel','warning','-y','-filter_complex_threads','2']
    filters=[]
    for i,c in enumerate(p['clips']):
        d=c['_duration']
        cmd+=['-ss',str(c['start']),'-t',str(d),'-i',c['source']]
        vf=(f'[{i}:v]setpts=PTS-STARTPTS,fps={fps},scale={w}:{h}:force_original_aspect_ratio=decrease,'
            f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p')
        if c['zoom']!=1 or c['zoom_end']!=1 or c['focus_x']!=c['focus_x_end'] or c['focus_y']!=c['focus_y_end']:
            n=max(c['_frames']-1,1)
            z=motion(c['zoom'],c['zoom_end'],0,n,'on')
            cx=motion(c['focus_x'],c['focus_x_end'],0,n,'on')
            cy=motion(c['focus_y'],c['focus_y_end'],0,n,'on')
            # Upscale before integer crop offsets to reduce stepping on slow moves.
            vf+=f",scale={w*2}:{h*2},zoompan=z='{z}':x='clip(iw*{cx}-iw/zoom/2,0,iw-iw/zoom)':y='clip(ih*{cy}-ih/zoom/2,0,ih-ih/zoom)':d=1:s={w}x{h}:fps={fps}"
        vf+=f',tpad=stop_mode=clone:stop_duration={1/fps},trim=end_frame={c["_frames"]},setpts=N/({fps}*TB)[v{i}]'
        filters.append(vf)
        audio=f'[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS' if c['_audio'] else 'anullsrc=r=48000:cl=stereo'
        chain=[f'volume={c["gain"]}',f'apad=whole_dur={d}',f'atrim=duration={d}','asetpts=PTS-STARTPTS']+afades(c,d)
        filters.append(audio+','+','.join(chain)+f'[a{i}]')
    joined=''.join(f'[v{i}][a{i}]' for i in range(len(p['clips'])))
    filters.append(joined+f'concat=n={len(p["clips"])}:v=1:a=1[base][original]')
    current='base'
    for i,e in enumerate(p['effects']):
        label=f'fx{i}'
        enable=f"gte(t,{e['start']})*lt(t,{e['end']})"
        if e['type']=='blur':
            filters.append(f"[{current}]gblur=sigma={e['sigma']}:enable='{enable}'[{label}]")
        else:
            cx=motion(e['x'],e['x_end'],e['start'],e['end'],'T')
            cy=motion(e['y'],e['y_end'],e['start'],e['end'],'T')
            distance=f'sqrt(pow((X-{cx})/{e["radius_x"]},2)+pow((Y-{cy})/{e["radius_y"]},2))'
            factor=f'(1-{e["dim"]}*clip(({distance}-1)/{e["feather"]},0,1))'
            filters.append(f"[{current}]geq=lum='lum(X,Y)*{factor}':cb='cb(X,Y)':cr='cr(X,Y)':enable='{enable}'[{label}]")
        current=label
    filters.append(f'[{current}]ass=behind.ass[behindtext]')
    current='behindtext'
    next_input=len(p['clips'])
    for i,o in enumerate(p['overlays']):
        duration=o['end']-o['start']
        if o['still']:
            cmd+=['-loop','1','-framerate',str(fps),'-t',str(duration),'-i',o['source']]
        else:
            cmd+=['-ss',str(o['source_start']),'-t',str(duration),'-i',o['source']]
        chain=['setpts=PTS-STARTPTS',f'fps={fps}']
        if 'crop' in o:
            x,y,cw,ch=o['crop']
            chain.append(f'crop={cw}:{ch}:{x}:{y}')
        ow,oh=o['width'],o['height']
        if o['fit']=='contain':
            chain += ['format=rgba',f'scale={ow}:{oh}:force_original_aspect_ratio=decrease',
                      f'pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color={o["pad_color"]}','setsar=1']
        else:
            chain += [f'scale={ow}:{oh}:force_original_aspect_ratio=increase',f'crop={ow}:{oh}', 'setsar=1','format=rgba']
        if o['border'] and not o['corner_radius']:
            chain.append(f'drawbox=x=0:y=0:w=iw:h=ih:color={o["border_color"]}:t={o["border"]}')
        if o['corner_radius']:
            r=o['corner_radius']
            alpha=f'alpha(X,Y)*lte(pow(max(abs(X-W/2)-(W/2-{r}),0),2)+pow(max(abs(Y-H/2)-(H/2-{r}),0),2),{r*r})'
            rgb=[f'{ch}(X,Y)' for ch in 'rgb']
            if o['border']:
                b=o['border']; inner=max(r-b,0)
                inside=f'lte(pow(max(abs(X-W/2)-(W/2-{b}-{inner}),0),2)+pow(max(abs(Y-H/2)-(H/2-{b}-{inner}),0),2),{inner*inner})'
                bc=o['border_color'][1:]
                rgb=[f'if({inside},{ch}(X,Y),{int(bc[j*2:j*2+2],16)})' for j,ch in enumerate('rgb')]
            chain.append(f"geq=r='{rgb[0]}':g='{rgb[1]}':b='{rgb[2]}':a='{alpha}'")
        if o['rotation'] or o['rotation_end']:
            # Fit every intermediate angle into the declared outer box, preserving corners.
            limit=math.radians(max(abs(o['rotation']),abs(o['rotation_end'])))
            angles=[0,limit]
            for critical in (math.atan2(oh,ow),math.atan2(ow,oh)):
                if critical<=limit:angles.append(critical)
            bound_w=max(ow*math.cos(a)+oh*math.sin(a) for a in angles)
            bound_h=max(ow*math.sin(a)+oh*math.cos(a) for a in angles)
            factor=min((ow-2)/bound_w,(oh-2)/bound_h)
            sw,sh=max(2,int(ow*factor)),max(2,int(oh*factor))
            angle=motion(o['rotation'],o['rotation_end'],0,o['move_duration'],easing=o['easing'])
            chain.extend([f'scale={sw}:{sh}',f'pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=black@0',
                          f"rotate=angle='{angle}*PI/180':ow=iw:oh=ih:c=none"])
        chain.append(f'colorchannelmixer=aa={o["opacity"]}')
        if o['fade_in']:
            chain.append(f'fade=t=in:st=0:d={o["fade_in"]}:alpha=1')
        if o['fade_out']:
            chain.append(f'fade=t=out:st={duration-o["fade_out"]}:d={o["fade_out"]}:alpha=1')
        chain.append(f'setpts=PTS-STARTPTS+{o["start"]}/TB')
        filters.append(f'[{next_input}:v]'+','.join(chain)+f'[overlay{i}]')
        next_input+=1
        x=motion(o['x'],o['x_end'],o['start'],o['start']+o['move_duration'],easing=o['easing'])
        y=motion(o['y'],o['y_end'],o['start'],o['start']+o['move_duration'],easing=o['easing'])
        filters.append(f"[{current}][overlay{i}]overlay=x='{x}':y='{y}':eof_action=pass:repeatlast=0:enable='gte(t,{o['start']})*lt(t,{o['end']})'[composite{i}]")
        current=f'composite{i}'
    filters.append(f'[{current}]ass=text.ass,format=yuv420p[video]')
    duck_count=sum(a['duck'] for a in p['audio'])
    mix=['[original]']
    if duck_count:
        filters.append('[original]asplit='+str(duck_count+1)+'[voice]'+''.join(f'[side{j}]' for j in range(duck_count)))
        mix=['[voice]']
    duck_index=0
    for i,a in enumerate(p['audio']):
        cmd+=['-ss',str(a['source_start']),'-t',str(a['duration']),'-i',a['source']]
        chain=['aresample=48000','aformat=sample_fmts=fltp:channel_layouts=stereo',
               'asetpts=PTS-STARTPTS',f'volume={a["gain"]}']+afades(a,a['duration'])
        chain.append(f'adelay={round(a["start"]*1000)}:all=1')
        filters.append(f'[{next_input}:a]'+','.join(chain)+f'[music{i}]')
        if a['duck']:
            filters.append(f'[music{i}]apad=whole_dur={total},atrim=duration={total}[padded{i}]')
            filters.append(f'[padded{i}][side{duck_index}]sidechaincompress=threshold=0.025:ratio=8:attack=15:release=350:makeup=1[ducked{i}]')
            mix.append(f'[ducked{i}]')
            duck_index+=1
        else:
            mix.append(f'[music{i}]')
        next_input+=1
    filters.append(''.join(mix)+f'amix=inputs={len(mix)}:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[audio]')
    return cmd,';\n'.join(filters)
