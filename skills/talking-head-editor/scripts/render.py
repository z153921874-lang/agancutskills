"""Render v1/v2 semantic edit plans with dynamic text and compositing."""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from editor import VERSION,ffmpeg_path,validate,write_text,graph,run,probe


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--ffmpeg')
    ap.add_argument('--check',action='store_true')
    a=ap.parse_args()
    ff=ffmpeg_path(a.ffmpeg)
    path,out=Path(a.plan).resolve(),Path(a.output).resolve()
    if out.suffix.lower()!='.mp4':
        raise ValueError('Output must end in .mp4')
    suffixes=['.mp4','.srt','.emphasis.srt','.ass','.behind.ass','.render.json','.source-map.json']
    if any(out.with_suffix(s).exists() for s in suffixes):
        raise ValueError('Output already exists; choose a new filename.')
    plan,total,mapping,warnings=validate(json.loads(path.read_text(encoding='utf-8-sig')),path.parent,ff)
    report={'version':VERSION,'planned_duration':total,'width':plan['width'],'height':plan['height'],
            'fps':plan['fps'],'warnings':warnings,'audio_review':'technical check only; listening review required'}
    if a.check:
        print(json.dumps({**report,'source_map':mapping},ensure_ascii=True,indent=2))
        return
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='talking-v2-',dir=out.parent) as d:
        tmp=Path(d)
        write_text(plan,tmp)
        cmd,filters=graph(plan,total,ff)
        (tmp/'graph.txt').write_text(filters,encoding='utf-8')
        cmd+=['-filter_complex_script','graph.txt','-map','[video]','-map','[audio]',
              '-t',str(total),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
              '-c:a','aac','-ar','48000','-ac','2','-movflags','+faststart','final.mp4']
        try:
            run(cmd,tmp)
        except Exception as ex:
            out.with_suffix('.error.txt').write_text(str(ex)+'\n\n'+filters,encoding='utf-8')
            raise
        info=probe(ff,tmp/'final.mp4')
        if not info['video'] or not info['audio'] or abs(info['duration']-total)>max(.12,2/plan['fps']):
            raise RuntimeError('Output stream/duration validation failed')
        report.update(actual_duration=info['duration'],output=str(out))
        # All media is encoded once; concatenation does not accumulate AAC encoder delays.
        for name,suffix in [('final.mp4','.mp4'),('text.ass','.ass'),('behind.ass','.behind.ass'),('caption.srt','.srt'),('emphasis.srt','.emphasis.srt')]:
            if (tmp/name).exists():
                shutil.copyfile(tmp/name,out.with_suffix(suffix))
        out.with_suffix('.source-map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
        out.with_suffix('.render.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
