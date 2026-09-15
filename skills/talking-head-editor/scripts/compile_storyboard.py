"""Compile an explicit editorial storyboard to a validated renderer plan."""
import argparse
import json
from pathlib import Path
from editor import validate, ffmpeg_path, keys, num


def compile_board(board, base, ff):
    keys(board,'canvas assets scenes')
    canvas=board.get('canvas',{})
    keys(canvas,'width height fps font')
    assets=board.get('assets',{})
    if not isinstance(assets,dict):raise ValueError('assets must be an object')
    for asset in assets.values():
        keys(asset,'source role provenance')
        if asset.get('role') not in ('evidence','illustration'):raise ValueError('Asset role required')
        if not isinstance(asset.get('provenance'),str) or not asset['provenance'].strip():
            raise ValueError('Asset provenance required; use unknown explicitly when unknown')
    scenes=board['scenes']
    if not isinstance(scenes,list) or not scenes:raise ValueError('scenes must be a nonempty list')
    clips=[];seen=set()
    for scene in scenes:
        keys(scene,'id source start end task takeaway zoom_end keywords visuals')
        for field in ('id','task','takeaway'):
            if not isinstance(scene.get(field),str) or not scene[field].strip():raise ValueError(field+' required')
        if scene['id'] in seen:raise ValueError('Duplicate scene id')
        seen.add(scene['id'])
        clips.append({k:scene[k] for k in ('source','start','end','zoom_end') if k in scene})
    raw={'version':2,**canvas,'clips':clips,'texts':[],'overlays':[]}
    normalized,total,mapping,warnings=validate(raw,base,ff)
    # Reuse the renderer's actual frame-rounded durations, never accumulate hand-rounded times.
    for clip,resolved in zip(raw['clips'],normalized['clips']):clip['source']=resolved['source']
    W,H=normalized['width'],normalized['height']
    rows=[]
    for scene,m in zip(scenes,mapping):
        duration=m['output_end']-m['output_start']
        def interval(item):
            start=num(item.get('start',0),0,duration)
            end=num(item.get('end',duration),0,duration)
            if end<=start:raise ValueError('Invalid scene-relative interval')
            return start+m['output_start'],end+m['output_start']
        row={'id':scene['id'],'task':scene['task'],'takeaway':scene['takeaway'],**m,'assets':[]}
        keyword_windows=[]
        for word in scene.get('keywords',[]):
            keys(word,'text start end animation')
            a,b=interval(word)
            if any(a<y and b>x for x,y in keyword_windows):raise ValueError('Keyword emphasis overlaps in scene '+scene['id'])
            keyword_windows.append((a,b))
            animation=word.get('animation','fade')
            if animation not in ('fade','pop','none'):raise ValueError('Unknown keyword animation')
            if len(word['text'])>16:warnings.append(scene['id']+': long emphasis text; shorten or split and inspect width')
            if b-a<max(.8,len(word['text'])/7):warnings.append(scene['id']+': emphasis may have too little reading time')
            raw['texts'].append({'start':a,'end':b,'text':word['text'],'kind':'emphasis',
                'x':W//2,'y':round(H*.10),'size':max(18,round(H*.04)),
                'pop':animation=='pop','fade_in':min(.15,(b-a)/4) if animation=='fade' else 0,
                'fade_out':min(.12,(b-a)/4) if animation=='fade' else 0,
                'animation_duration':min(.3,b-a),'color':'#FFE36B'})
        occupied=[]
        for visual in scene.get('visuals',[]):
            keys(visual,'asset start end layout source_start fallback fit rotation rotation_end move_duration easing')
            if visual.get('fallback','error') not in ('error','talking_head'):raise ValueError('Unknown fallback')
            ref=visual['asset']
            if ref not in assets:raise ValueError('Unknown asset '+ref)
            asset=assets[ref];source=(base/asset['source']).resolve()
            a,b=interval(visual);layout=visual.get('layout','full')
            if layout not in ('full','card_left','card_right'):raise ValueError('Unsupported layout')
            if not source.is_file():
                if visual.get('fallback')=='talking_head':
                    warnings.append(f'{scene["id"]}: asset {ref} missing; explicit talking_head fallback used')
                    row['assets'].append({'id':ref,'status':'fallback','role':asset['role']})
                    continue
                raise ValueError('Missing asset: '+str(source))
            for x,y,other in occupied:
                if a<y and b>x and (layout==other or 'full' in (layout,other)):
                    raise ValueError('Conflicting visual layers in scene '+scene['id'])
            occupied.append((a,b,layout))
            if layout=='full':
                rect={'x':0,'y':0,'width':W,'height':H}
            else:
                # Keep the lower subtitle area free. This is a fixed card layout, not face detection.
                cw=round(W*.38)//2*2;ch=round(H*.52)//2*2
                rect={'x':round(W*(.06 if layout=='card_left' else .56)),'y':round(H*.23),
                    'width':cw,'height':ch,'corner_radius':18,'border':3}
            raw['overlays'].append({'source':str(source),'source_start':visual.get('source_start',0),
                'start':a,'end':b,'fit':visual.get('fit','contain'),
                **{k:visual[k] for k in ('rotation','rotation_end','move_duration','easing') if k in visual},**rect})
            row['assets'].append({'id':ref,'status':'ready','role':asset['role'],'provenance':asset['provenance']})
        rows.append(row)
    _,_,_,render_warnings=validate(raw,base,ff)
    report={'duration':total,'source_map':mapping,'scenes':rows,'warnings':list(dict.fromkeys(warnings+render_warnings)),
        'review_required':['Meaning and evidence are editorial checks, not inferred by compiler.',
            'Full overlays cover baked-in captions; preserve/rebuild dialogue captions if necessary.',
            'Card placement does not detect faces; inspect framing, crop, text and listening sync.']}
    return raw,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--storyboard',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--ffmpeg')
    a=p.parse_args();src=Path(a.storyboard).resolve();out=Path(a.output_dir).resolve()
    if out.exists():raise ValueError('Output directory exists')
    plan,report=compile_board(json.loads(src.read_text(encoding='utf-8-sig')),src.parent,ffmpeg_path(a.ffmpeg))
    out.mkdir(parents=True)
    for name,data in [('plan.json',plan),('editorial.json',report),('source-map.json',report['source_map'])]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'validated','duration':report['duration'],'warnings':report['warnings']}))


if __name__=='__main__':main()
