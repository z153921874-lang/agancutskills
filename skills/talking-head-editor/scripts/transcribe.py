"""Local-only faster-whisper transcription; requires a downloaded model directory."""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from editor import ffmpeg_path,probe,run,num,stamp


def caption_chunks(segments,max_chars=22,max_seconds=4):
    chunks=[]
    for s in segments:
        words=s['words']
        if not words:
            chunks.append({'start':s['start'],'end':s['end'],'text':s['text']})
            continue
        group=[]
        for word in words:
            if group and (len(''.join(x['word'] for x in group))+len(word['word'])>max_chars or word['end']-group[0]['start']>max_seconds):
                chunks.append({'start':group[0]['start'],'end':group[-1]['end'],'text':''.join(x['word'] for x in group).strip()})
                group=[]
            group.append(word)
            if word['word'].rstrip().endswith(('。','！','？','!','?')):
                chunks.append({'start':group[0]['start'],'end':group[-1]['end'],'text':''.join(x['word'] for x in group).strip()})
                group=[]
        if group:
            chunks.append({'start':group[0]['start'],'end':group[-1]['end'],'text':''.join(x['word'] for x in group).strip()})
    return [c for c in chunks if c['end']>c['start'] and c['text']]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',required=True)
    ap.add_argument('--model',required=True,help='Local faster-whisper model directory; never an online model name')
    ap.add_argument('--output',required=True,help='JSON output; SRT shares its stem')
    ap.add_argument('--dependency-dir')
    ap.add_argument('--ffmpeg')
    ap.add_argument('--start',type=float,default=0)
    ap.add_argument('--duration',type=float)
    ap.add_argument('--language',default='zh')
    ap.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    ap.add_argument('--compute-type',default='int8')
    ap.add_argument('--vocabulary',default='',help='Names/terms to aid recognition, not new dialogue')
    ap.add_argument('--max-chars',type=int,default=22)
    ap.add_argument('--max-seconds',type=float,default=4)
    a=ap.parse_args()
    if a.dependency_dir:
        sys.path.insert(0,str(Path(a.dependency_dir).resolve()))
    from faster_whisper import WhisperModel
    model=Path(a.model).resolve()
    if not (model/'model.bin').is_file():
        raise ValueError('Local model.bin is missing; download models separately with user authorization.')
    source,out=Path(a.input).resolve(),Path(a.output).resolve()
    if out.suffix.lower()!='.json':
        raise ValueError('Output must end in .json')
    if out.exists() or out.with_suffix('.srt').exists():
        raise ValueError('Output already exists')
    ff=ffmpeg_path(a.ffmpeg)
    info=probe(ff,source)
    if not info['audio']:
        raise ValueError('Input has no audio; no transcript was produced')
    start=num(a.start,0,info['duration'])
    duration=num(a.duration if a.duration is not None else info['duration']-start,.001,info['duration']-start)
    num(a.max_chars,4,100);num(a.max_seconds,.5,10)
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='asr-',dir=out.parent) as d:
        audio=Path(d)/'speech.wav'
        run([ff,'-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(duration),'-vn','-ac','1','-ar','16000',str(audio)])
        m=WhisperModel(str(model),device=a.device,compute_type=a.compute_type,cpu_threads=4,local_files_only=True)
        segments,meta=m.transcribe(str(audio),language=a.language,beam_size=5,word_timestamps=True,
                                  vad_filter=True,initial_prompt=a.vocabulary or None)
        items=[]
        for s in segments:
            items.append({'start':s.start+start,'end':s.end+start,'text':s.text.strip(),
                          'avg_logprob':s.avg_logprob,'no_speech_prob':s.no_speech_prob,
                          'words':[{'start':w.start+start,'end':w.end+start,'word':w.word,'probability':w.probability} for w in (s.words or [])]})
    captions=caption_chunks(items,a.max_chars,a.max_seconds)
    words=[w for s in items for w in s['words']]
    gaps=[{'start':left['end']+.12,'end':right['start']-.12,'reason':'ASR word gap, unconfirmed; may contain meaningful breath or non-speech sound'}
          for left,right in zip(words,words[1:]) if right['start']-left['end']>.6]
    result={'source':str(source),'model':str(model),'language':meta.language,'start':start,'duration':duration,
            'time_basis':'source seconds','segments':items,'captions':captions,'gap_candidates':gaps,
            'review':'Unreviewed machine transcript; check names, negation, numbers and cut points. Gaps are candidates, never automatic deletions.'}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    blocks=[f'{i}\n{stamp(s["start"],True)} --> {stamp(s["end"],True)}\n{s["text"]}\n' for i,s in enumerate(captions,1)]
    out.with_suffix('.srt').write_text('\n'.join(blocks),encoding='utf-8-sig')
    print(json.dumps({'segments':len(items),'output':str(out),'status':'machine transcript, needs review'},ensure_ascii=True))


if __name__=='__main__':
    main()
