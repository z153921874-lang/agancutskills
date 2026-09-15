"""Report observable packaging facts and review prompts; never score aesthetic quality."""
import argparse
import json
from pathlib import Path


def inspect(plan):
    w,h=plan['width'],plan['height'];fps=plan.get('fps',25)
    duration=sum(round((c['end']-c['start'])*fps)/fps for c in plan['clips'])
    overlays=plan.get('overlays',[]);texts=[t for t in plan.get('texts',[]) if t.get('kind')=='emphasis']
    still=[o for o in overlays if o.get('still',Path(o['source']).suffix.lower() in ('.png','.jpg','.jpeg','.webp'))]
    full=[o for o in overlays if o['width']>=w*.8 and o['height']>=h*.75]
    outer=[t for t in texts if t.get('y',h*.15)<h*.08 or t.get('y',h*.15)>h*.92]
    spans=sorted((max(0,o['start']),min(duration,o['end'])) for o in overlays)
    union=0;end=0
    for a,b in spans:
        union+=max(0,b-max(a,end));end=max(end,b)
    prompts=[]
    if not full:prompts.append('没有大幅资料/图解叠层：检查重要概念是否始终只靠真人讲述。基础clips也可能包含资料，此指标不能识别它们。')
    if overlays and len(still)==len(overlays):prompts.append('新增素材全部为静态图片：检查每张是否解释关系，是否需要逐项显现或具体动作素材。')
    if texts and len(outer)==len(texts):prompts.append('强调文字全部位于边缘窄区：检查是否只做了章节标签，缺少主画面视觉重音。')
    layouts={(o['x'],o['y'],o['width'],o['height']) for o in overlays}
    if len(overlays)>1 and len(layouts)==1:prompts.append('叠层版式完全一致：检查是否用同一张总结卡应付不同句子任务。')
    if not plan.get('audio'):prompts.append('没有新增声音轨：说明是否保留纯原声的有意选择，并完成切口试听；不要求为凑效果而加配乐。')
    return {'duration':round(duration,3),'overlays':len(overlays),'still_overlays':len(still),
        'large_overlays':len(full),'overlay_union_seconds':round(union,3),'emphasis_events':len(texts),
        'outer_band_emphasis':len(outer),'review_prompts':prompts,
        'not_evaluated':['原片自带镜头变化','实际语义与资料准确性','画面美观','主观听觉质量'],
        'status':'editorial review required; no automatic reference-match score'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();out=Path(a.output)
    if out.exists():raise ValueError('Output exists')
    result=inspect(json.loads(Path(a.plan).read_text(encoding='utf-8-sig')))
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
