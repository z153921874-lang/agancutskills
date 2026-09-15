"""Seeded local object tracking for label keyframes. No identity recognition or auto approval."""
import argparse
import json
from pathlib import Path
from editor import num,integer


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--start',type=float,default=0)
    ap.add_argument('--duration',type=float,required=True)
    ap.add_argument('--box',nargs=4,type=int,required=True,metavar=('X','Y','W','H'))
    ap.add_argument('--canvas',nargs=2,type=int)
    ap.add_argument('--sample-every',type=float,default=.12)
    ap.add_argument('--label-offset',type=float,default=-20)
    a=ap.parse_args()
    import cv2
    import numpy as np
    out=Path(a.output).resolve()
    if out.exists():
        raise ValueError('Output already exists')
    cap=cv2.VideoCapture(str(Path(a.input).resolve()))
    fps=cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps<=0:
        raise ValueError('Cannot read video')
    w,h=int(cap.get(3)),int(cap.get(4))
    length=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps
    start=num(a.start,0,length)
    duration=num(a.duration,1/fps,min(120,length-start))
    step=max(1,round(num(a.sample_every,.04,1)*fps))
    box=[int(x) for x in a.box]
    if min(box[:2])<0 or min(box[2:])<8 or box[0]+box[2]>w or box[1]+box[3]>h:
        raise ValueError('Seed box outside frame')
    cw,ch=a.canvas or [w,h]
    integer(cw,64,4096);integer(ch,64,4096)
    num(a.label_offset,-ch,ch)
    scale=min(cw/w,ch/h)
    pad_x,pad_y=(cw-w*scale)/2,(ch-h*scale)/2
    working=min(1,640/w)
    cap.set(cv2.CAP_PROP_POS_MSEC,start*1000)
    ok,frame=cap.read()
    if not ok:
        raise ValueError('Cannot read seed frame')
    tracker=cv2.TrackerMIL_create()
    small=cv2.resize(frame,(round(w*working),round(h*working)))
    tracker.init(small,tuple(round(x*working) for x in box))
    previous=cv2.resize(small,(32,32)).astype(np.float32)
    points=[]
    boxes=[]
    failed=None
    frames=round(duration*fps)
    current=box
    for i in range(frames):
        if i:
            ok,frame=cap.read()
            if not ok:
                failed={'time':i/fps,'reason':'Source ended'};break
            small=cv2.resize(frame,(round(w*working),round(h*working)))
            tiny=cv2.resize(small,(32,32)).astype(np.float32)
            if np.mean(np.abs(tiny-previous))>45:
                failed={'time':i/fps,'reason':'Possible shot change; reseed tracking'};break
            previous=tiny
            ok,b=tracker.update(small)
            if not ok:
                failed={'time':i/fps,'reason':'Tracker reported failure'};break
            current=[x/working for x in b]
        if i%step==0 or i==frames-1:
            x,y,bw,bh=current
            points.append({'time':round(i/fps,6),'x':min(cw,max(0,(x+bw/2)*scale+pad_x)),
                           'y':min(ch,max(0,y*scale+pad_y+a.label_offset))})
            boxes.append({'source_time':start+i/fps,'box':current})
    cap.release()
    if points and not failed:
        points.append({**points[-1],'time':frames/fps})
    result={'source':str(Path(a.input).resolve()),'start':start,'duration':frames/fps,
            'canvas':[cw,ch],'keyframes':points,'boxes':boxes,'failure':failed,
            'status':'unreviewed MIL tracking; no confidence score',
            'limitations':'May drift. Requires fixed unzoomed letterbox geometry and manual review. Reseed after cuts/occlusion.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'keyframes':len(points),'failure':failed,'output':str(out)},ensure_ascii=True))


if __name__=='__main__':
    main()
