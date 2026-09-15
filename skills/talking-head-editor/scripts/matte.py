"""Experimental local RVM human matting. Produces silent straight-alpha MOV, not identity selection."""
import argparse
import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from editor import ffmpeg_path,num,integer,color,probe


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True)
    ap.add_argument('--model',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--dependency-dir')
    ap.add_argument('--start',type=float,default=0)
    ap.add_argument('--duration',type=float,required=True)
    ap.add_argument('--width',type=int,default=640)
    ap.add_argument('--crop',nargs=4,type=int,metavar=('X','Y','W','H'))
    ap.add_argument('--outline',type=int,default=0)
    ap.add_argument('--glow',type=float,default=0)
    ap.add_argument('--color',default='#FFE36B')
    ap.add_argument('--ffmpeg')
    a=ap.parse_args()
    if a.dependency_dir:
        sys.path.insert(0,str(Path(a.dependency_dir).resolve()))
    import cv2
    import numpy as np
    import onnxruntime as ort
    out=Path(a.output).resolve()
    if out.suffix.lower()!='.mov':
        raise ValueError('Output must be .mov (qtrle alpha)')
    if out.exists() or out.with_suffix('.matte.json').exists():
        raise ValueError('Output already exists')
    model=Path(a.model).resolve()
    if not model.is_file():
        raise ValueError('Local ONNX model missing')
    ff=ffmpeg_path(a.ffmpeg)
    source=Path(a.input).resolve()
    info=probe(ff,source)
    start=num(a.start,0,info['duration'])
    dur=num(a.duration,.04,min(120,info['duration']-start))
    width=integer(a.width,128,1920)
    outline=integer(a.outline,0,64)
    glow=num(a.glow,0,64)
    rgb=np.array([int(color(a.color)[i:i+2],16)/255 for i in (1,3,5)],np.float32)
    cap=cv2.VideoCapture(str(source))
    fps=cap.get(cv2.CAP_PROP_FPS)
    x,y,cw,ch=a.crop or [0,0,info['width'],info['height']]
    if min(x,y)<0 or min(cw,ch)<2 or x+cw>info['width'] or y+ch>info['height']:
        raise ValueError('Invalid crop')
    height=round(ch*width/cw)
    cap.set(cv2.CAP_PROP_POS_MSEC,start*1000)
    options=ort.SessionOptions();options.intra_op_num_threads=4
    session=ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
    if [i.name for i in session.get_inputs()]!=['src','r1i','r2i','r3i','r4i','downsample_ratio']:
        raise ValueError('Unsupported ONNX signature: expected RVM')
    if session.get_inputs()[0].type!='tensor(float)':
        raise ValueError('CPU path requires fp32 RVM')
    rec=[np.zeros((1,1,1,1),np.float32) for _ in range(4)]
    ratio=np.array([min(1,384/max(width,height))],np.float32)
    out.parent.mkdir(parents=True,exist_ok=True)
    frames=round(dur*fps)
    processed=0
    previous=None
    resets=[]
    with tempfile.TemporaryDirectory(prefix='matte-',dir=out.parent) as d:
        tmp=Path(d)
        with (tmp/'encode.log').open('wb') as log:
            proc=subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f'{width}x{height}',
                                   '-r',str(fps),'-i','-','-an','-c:v','qtrle','-pix_fmt','argb',str(tmp/'subject.mov')],stdin=subprocess.PIPE,stderr=log)
            try:
                for i in range(frames):
                    ok,bgr=cap.read()
                    if not ok:
                        raise ValueError('Video ended before requested duration')
                    bgr=cv2.resize(bgr[y:y+ch,x:x+cw],(width,height))
                    tiny=cv2.resize(bgr,(32,32)).astype(np.float32)
                    if previous is not None and np.mean(np.abs(tiny-previous))>45:
                        rec=[np.zeros((1,1,1,1),np.float32) for _ in range(4)]
                        resets.append(i/fps)
                    previous=tiny
                    frame=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype(np.float32)/255
                    inputs={'src':frame.transpose(2,0,1)[None], 'downsample_ratio':ratio}
                    inputs.update({f'r{j+1}i':r for j,r in enumerate(rec)})
                    fgr,pha,*rec=session.run(None,inputs)
                    foreground=fgr[0].transpose(1,2,0).clip(0,1)
                    alpha=pha[0,0].clip(0,1)
                    if outline or glow:
                        expanded=cv2.dilate(alpha,np.ones((outline*2+1,outline*2+1),np.uint8)) if outline else alpha
                        extra=expanded
                        if glow:
                            extra=np.maximum(extra,cv2.GaussianBlur(expanded,(0,0),glow)*.85)
                        final_alpha=alpha+extra*(1-alpha)
                        foreground=(foreground*alpha[:,:,None]+rgb*extra[:,:,None]*(1-alpha[:,:,None]))/np.maximum(final_alpha[:,:,None],1e-6)
                        alpha=final_alpha
                    rgba=np.concatenate((foreground,alpha[:,:,None]),axis=2)
                    proc.stdin.write((rgba.clip(0,1)*255).astype(np.uint8).tobytes())
                    processed+=1
                proc.stdin.close()
                if proc.wait()!=0:
                    raise RuntimeError('Alpha encoding failed')
            except Exception:
                proc.kill();proc.wait();raise
        shutil.copyfile(tmp/'subject.mov',out)
    cap.release()
    report={'source':str(source),'start':start,'duration':processed/fps,'width':width,'height':height,
            'fps':fps,'crop':[x,y,cw,ch],'scene_resets':resets,'outline':outline,'glow':glow,
            'audio':'none; retain the base clip audio','status':'experimental, requires visual review',
            'limitations':'All humans may be included; no identity isolation; hair, motion and occlusion need inspection.'}
    out.with_suffix('.matte.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':
    main()
