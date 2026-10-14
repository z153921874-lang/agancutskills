"""Conservative local video cleanup. Not neural super-resolution or face recovery."""
import argparse,json,subprocess,math
from pathlib import Path
from editor import ffmpeg_path,probe

def quality_filter(denoise=.8,sharpness=.18):
    if not math.isfinite(denoise) or not 0<=denoise<=2:raise ValueError('denoise must be in [0,2]')
    if not math.isfinite(sharpness) or not 0<=sharpness<=.5:raise ValueError('sharpness must be in [0,.5]')
    return f'hqdn3d={denoise}:{denoise}:{denoise*2.25}:{denoise*2.25},unsharp=5:5:{sharpness}:3:3:0,setsar=1'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--start',type=float,default=0);ap.add_argument('--duration',type=float)
    ap.add_argument('--denoise',type=float,default=.8);ap.add_argument('--sharpness',type=float,default=.18)
    ap.add_argument('--ffmpeg');a=ap.parse_args()
    src=Path(a.input).resolve();out=Path(a.output).resolve()
    if out.exists() or out==src:raise ValueError('output must be a new file')
    ff=ffmpeg_path(a.ffmpeg);info=probe(ff,src)
    dur=info['duration']-a.start if a.duration is None else a.duration
    if not math.isfinite(a.start) or not math.isfinite(dur) or a.start<0 or dur<=0 or a.start+dur>info['duration']+.05:raise ValueError('invalid range')
    filters=quality_filter(a.denoise,a.sharpness);out.parent.mkdir(parents=True,exist_ok=True)
    # Silent visual intermediate; keep source audio separately, exactly once.
    subprocess.run([ff,'-v','error','-ss',str(a.start),'-i',str(src),'-t',str(dur),'-vf',filters,'-an','-c:v','libx264','-preset','fast','-crf','15','-pix_fmt','yuv420p',str(out)],check=True)
    report={'source':str(src),'source_range':[a.start,a.start+dur],'native_size':[info['width'],info['height']],'filters':filters,'audio':'none; preserve the original track separately','neural_super_resolution':False,'limits':'No missing detail, identity, hair or text is reconstructed; choose settings by matched-frame and motion comparison.'}
    out.with_suffix('.quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
