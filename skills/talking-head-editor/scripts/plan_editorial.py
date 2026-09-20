"""Plan an entire edit, resolve source-timed emphasis, and build a human review queue.

Consumes explicit editorial decisions. Does not infer semantics, prosody or approval.
"""
import argparse
import hashlib
import html
import json
import math
import shutil
from pathlib import Path


def number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Expected finite number')
    return float(value)


def required(row,key):
    value=row.get(key)
    if not isinstance(value,str) or not value.strip():raise ValueError(key+' must be nonempty text')
    return value


def analyze(plan,mapping):
    fps=number(plan['fps']);duration=number(plan['duration'])
    if not 1<=fps<=120 or duration<=0:raise ValueError('Invalid fps or duration')
    frame=1/fps;eps=1e-6
    def tick(t):return math.ceil((t-eps)*fps)/fps
    def aligned(t):return abs(t*fps-round(t*fps))<1e-4
    scenes=plan['scenes'];cues=plan.get('cues',[])
    if not isinstance(scenes,list) or not scenes:raise ValueError('Scenes required')
    if not isinstance(cues,list):raise ValueError('Cues must be a list')
    if not isinstance(mapping,list) or not mapping:raise ValueError('Source map required')
    previous=0
    for m in mapping:
        required(m,'source')
        a,b,x,y=[number(m[k]) for k in ('source_start','source_end','output_start','output_end')]
        if min(a,x)<0 or b<=a or y<=x or abs(x-previous)>eps:raise ValueError('Source map must be positive, continuous and ordered')
        if abs((b-a)-(y-x))>frame+eps:raise ValueError('Speed changes are unsupported; mapping must be 1:1 within frame rounding')
        if not aligned(x) or not aligned(y):raise ValueError('Output map must align to frame grid')
        previous=y
    if abs(previous-duration)>eps:raise ValueError('Duration disagrees with source map')
    roles=('host','broll','evidence','metaphor','relationship','comparison')
    index={};warnings=[];queue=[];previous=0
    def item(key,kind,start,end,reason,expected):
        queue.append({'id':key,'kind':kind,'start':round(max(0,start),6),'end':round(min(duration,end),6),'reason':reason,'expected':expected,'status':'pending','note':''})
    for s in scenes:
        key=required(s,'id')
        if key in index:raise ValueError('Duplicate scene id')
        a,b=number(s['start']),number(s['end'])
        if abs(a-previous)>eps or b<=a or b>duration+eps:raise ValueError('Scenes must cover the edit without gaps or overlaps')
        if not aligned(a) or not aligned(b):raise ValueError('Scene boundary must align to frame grid')
        if s.get('role') not in roles:raise ValueError('Unknown scene role')
        for field in ('takeaway','focus','entry','exit'):required(s,field)
        assets=s.get('assets',[])
        if not isinstance(assets,list) or any(not isinstance(v,str) or not v for v in assets):raise ValueError('Asset IDs must be nonempty strings')
        if s['role']!='host' and not assets:warnings.append({'scene':key,'code':'no_assets','message':'解释画面没有素材标识，需准备素材或调整分镜。'})
        callback=s.get('callback')
        if callback is not None:
            target=callback.get('scene');required(callback,'new_meaning')
            if target not in index:raise ValueError('Callback must reference an earlier scene')
            if not set(assets)&set(index[target].get('assets',[])):
                warnings.append({'scene':key,'code':'callback_identity','message':'回调没有共用素材标识，检查是否仍能认出前文对象。'})
        index[key]=s;previous=b
        item('scene:'+key,'picture',a,b,'检查该段视觉任务、焦点和阅读停顿',s['takeaway']+'；焦点：'+s['focus'])
    if abs(previous-duration)>eps:raise ValueError('Scene plan does not cover full duration')
    for i in range(2,len(scenes)):
        group=scenes[i-2:i+1]
        if len({s['focus'] for s in group})==1 and all(s['role']!='host' for s in group):
            warnings.append({'scene':scenes[i]['id'],'code':'repeated_focus','message':'连续三段使用相同焦点描述，检查是否机械套版；此提示不自动判定审美。'})
    texts=[];resolved=[];cue_ids=set()
    for c in cues:
        key=required(c,'id');text=required(c,'text')
        if key in cue_ids:raise ValueError('Duplicate cue id')
        cue_ids.add(key)
        ci=c['clip_index']
        if isinstance(ci,bool) or not isinstance(ci,int) or not 0<=ci<len(mapping):raise ValueError('Invalid clip_index')
        scene=index.get(c['scene'])
        if scene is None:raise ValueError('Cue references missing scene')
        basis=c['timing_basis']
        if basis not in ('word_verified','subtitle_verified','asr_unverified'):raise ValueError('Unknown timing basis')
        required(c,'evidence')
        a,b=number(c['source_start']),number(c['source_end']);m=mapping[ci]
        if b<=a or a<m['source_start']-eps or b>m['source_end']+eps:raise ValueError('Cue crosses a cut or refers to deleted source words')
        spoken=m['output_start']+a-m['source_start'];spoken_end=min(m['output_end'],m['output_start']+b-m['source_start'])
        if spoken<scene['start']-eps or spoken_end>scene['end']+eps:raise ValueError('Spoken cue is outside its scene')
        lead=number(c.get('lead',0));hold=number(c.get('hold',.8))
        if not 0<=lead<=1 or not 0<hold<=10:raise ValueError('Lead or hold out of range')
        start=tick(max(scene['start'],m['output_start'],spoken-lead))
        end=min(scene['end'],m['output_end'],tick(max(spoken_end,start+hold)))
        if end<=start:raise ValueError('Empty cue after frame rounding')
        if lead>frame+eps:warnings.append({'cue':key,'code':'early_cue','message':'关键词有意提前超过一帧，需检查是否抢先泄露结论。'})
        if basis!='word_verified':warnings.append({'cue':key,'code':'timing_review','message':'不是已核对词级时间，需回听；短句字幕不能证明精确重音同步。'})
        if end-start+eps<hold:warnings.append({'cue':key,'code':'short_hold','message':'关键词停留被剪口或场景结束截短，考虑删字、换位置或调整剪口。'})
        if end-start<max(.8,len(text)/7):warnings.append({'cue':key,'code':'reading_time','message':'可能来不及读完，需实际预览；不是自动审美判分。'})
        if any(start<r['end']-eps and end>r['start']+eps for r in resolved):
            warnings.append({'cue':key,'code':'emphasis_overlap','message':'存在同时出现的强调词，确认属于有意对比而非重复叠字。'})
        row={'id':key,'text':text,'scene':c['scene'],'clip_index':ci,'start':round(start,6),'end':round(end,6),'spoken_start':round(spoken,6),'timing_basis':basis,'evidence':c['evidence']}
        resolved.append(row)
        texts.append({'start':row['start'],'end':row['end'],'text':text,'kind':'emphasis','fade_in':min(.12,(end-start)/4),'fade_out':min(.12,(end-start)/4)})
        item('cue:'+key,'timing',start-.5,end+.5,'回听关键词入场前后；核对原话、重音与字幕',text+'；定位依据：'+basis)
    for i,m in enumerate(mapping[1:],1):
        t=m['output_start'];item('cut:'+str(i),'listening',t-.45,t+.75,'试听剪口两侧，检查切字、呼吸、语气与背景声突变','接点自然，词句完整；需要时保留更多原声')
    item('full','full_review',0,duration,'完整连续观看和试听，短窗检查不能代替整片','检查信息推进、整体节奏、声音和结尾完整性')
    return {'version':'2.9','duration':duration,'fps':fps,'scenes':scenes,'cues':resolved,'emphasis_texts':texts,'warnings':warnings,'review_queue':queue,'review_status':'pending','limitations':['Explicit editorial plan; no automatic semantic or prosody detection.','Generated checks never imply human listening or visual approval.']}


def review_html(report,video,media_url=None):
    payload=json.dumps(report,ensure_ascii=False).replace('<','\\u003c')
    uri=html.escape(media_url or Path(video).resolve().as_uri(),quote=True)
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>口播审片</title>
<style>body{margin:0;background:#151a18;color:#e7eee8;font:16px system-ui}main{max-width:1100px;margin:auto;padding:24px}h1{font-size:26px}p{color:#aebcaf}video{width:100%;max-height:68vh;background:#000;border-radius:12px}.layout{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{padding:16px;background:#242e28;border-radius:10px;margin:12px 0}button,select,textarea{font:inherit;padding:9px;border-radius:5px;border:1px solid #526352}button{background:#b4ff70;cursor:pointer}textarea{box-sizing:border-box;width:100%;margin-top:8px;min-height:55px}select{margin-left:8px}#list{max-height:80vh;overflow:auto}small{color:#b0bcae}.row{display:flex;gap:8px;flex-wrap:wrap}#warn{color:#f5cc86}@media(max-width:750px){.layout{grid-template-columns:1fr}}</style>
<main><h1>口播审片</h1><p>逐段检查后记录结果。播放不等于验收通过；修改成片后应重新生成页面。</p><div class="layout"><section><video id="video" controls preload="metadata" src="'''+uri+'''"></video><p id="active">选择右侧检查项开始播放。</p><div class="row"><button id="whole">连续播放全片</button><button id="save">导出审片记录</button></div><p id="count"></p><p id="warn"></p></section><section id="list"></section></div></main>
<script id="payload" type="application/json">'''+payload+'''</script><script>
const report=JSON.parse(document.querySelector('#payload').textContent),v=document.querySelector('#video');let stop=null;
const statusNames={pending:'待检查',pass:'已检查通过',revise:'需要修改'};
function count(){const q=report.review_queue;document.querySelector('#count').textContent=`待检查 ${q.filter(x=>x.status==='pending').length} 项 · 需修改 ${q.filter(x=>x.status==='revise').length} 项 · 已通过 ${q.filter(x=>x.status==='pass').length} 项`;}
v.addEventListener('timeupdate',()=>{if(stop!==null&&v.currentTime>=stop){v.pause();stop=null;}});
v.addEventListener('error',()=>document.querySelector('#active').textContent='视频无法加载，请确认原文件仍在原路径。');
for(const r of report.review_queue){const a=document.createElement('article'),h=document.createElement('b'),p=document.createElement('p'),small=document.createElement('small'),button=document.createElement('button'),select=document.createElement('select'),note=document.createElement('textarea');h.textContent=`${r.start.toFixed(2)}–${r.end.toFixed(2)} 秒`;p.textContent=r.reason;small.textContent=r.expected;button.textContent='播放这一段';button.onclick=()=>{stop=r.end;v.currentTime=r.start;v.play().catch(()=>{});document.querySelector('#active').textContent=r.expected;};for(const [key,label] of Object.entries(statusNames)){const opt=document.createElement('option');opt.value=key;opt.textContent=label;select.append(opt);}select.onchange=()=>{r.status=select.value;count();};note.placeholder='发现的问题、具体时间及修改办法';note.oninput=()=>r.note=note.value;const row=document.createElement('div');row.append(button,select);a.append(h,p,small,row,note);document.querySelector('#list').append(a);}
document.querySelector('#whole').onclick=()=>{stop=null;v.currentTime=0;v.play().catch(()=>{});};
document.querySelector('#save').onclick=()=>{const result={video:report.video,generated_plan_sha256:report.plan_sha256,reviewed_at:new Date().toISOString(),status:report.review_queue.every(x=>x.status==='pass')?'reviewer_marked_pass':'incomplete',review_queue:report.review_queue};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='审片记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
document.querySelector('#warn').textContent=`计划中有 ${report.warnings.length} 条需复核提示，详见同目录 review.json。`;count();
</script></html>'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True);p.add_argument('--source-map',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--video');p.add_argument('--copy-video',action='store_true')
    a=p.parse_args();out=Path(a.output_dir)
    if out.exists():raise ValueError('Output directory exists; choose a new one')
    if a.copy_video and not a.video:raise ValueError('--copy-video requires --video')
    source=Path(a.plan).read_bytes();plan=json.loads(source.decode('utf-8-sig'))
    report=analyze(plan,json.loads(Path(a.source_map).read_text(encoding='utf-8-sig')))
    report['plan_sha256']=hashlib.sha256(source).hexdigest()
    page=None
    if a.video:
        video=Path(a.video).resolve()
        if not video.is_file():raise ValueError('Video not found')
        with video.open('rb') as f:
            digest=hashlib.sha256()
            for block in iter(lambda:f.read(1024*1024),b''):digest.update(block)
        report['video']={'path':str(video),'sha256':digest.hexdigest()}
        media_name='review-video'+video.suffix.lower()
        page=review_html(report,video,media_name if a.copy_video else None)
    out.mkdir(parents=True)
    (out/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'emphasis.json').write_text(json.dumps(report['emphasis_texts'],ensure_ascii=False,indent=2),encoding='utf-8')
    if page:(out/'审片.html').write_text(page,encoding='utf-8')
    if a.copy_video:shutil.copy2(video,out/media_name)
    print(json.dumps({'duration':report['duration'],'cues':len(report['cues']),'warnings':len(report['warnings']),'review_items':len(report['review_queue']),'review_status':'pending'}))


if __name__=='__main__':main()
