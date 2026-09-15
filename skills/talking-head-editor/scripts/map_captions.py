"""Map source word timestamps to an edited timeline without repeating deleted words."""
import argparse
import json
from pathlib import Path
from editor import num, stamp


def map_words(transcript, mapping, max_chars=22, max_seconds=4):
    source=Path(transcript['source']).resolve()
    captions=[]
    review=[]
    words=[w for s in transcript['segments'] for w in s.get('words',[])]
    if not words:
        raise ValueError('Word timestamps required; segment-only text cannot be safely split')
    for w in words:
        if num(w['end']) < num(w['start']):
            raise ValueError('Reversed word interval')
    previous=0
    for index,m in enumerate(mapping):
        a,b,x,y=[num(m[k]) for k in ('source_start','source_end','output_start','output_end')]
        if b<=a or y<=x or x<previous-0.0001:
            raise ValueError('Invalid or overlapping map intervals')
        previous=y
        if Path(m['source']).resolve()!=source:
            review.append({'clip_index':index,'reason':'different_source_no_transcript'})
            continue
        coverage_start=transcript.get('start',min(w['start'] for w in words))
        coverage_end=coverage_start+transcript['duration'] if 'duration' in transcript else max(w['end'] for w in words)
        if a<coverage_start-.001 or b>coverage_end+.001:
            review.append({'clip_index':index,'reason':'transcript_does_not_cover_full_clip'})
        group=[]
        def flush():
            if group:
                captions.append({'start':group[0]['start'],'end':group[-1]['end'],
                    'text':''.join(w['word'] for w in group).strip(),'clip_index':index})
                group.clear()
        for w in words:
            ws,we=w['start'],w['end']
            if we<=a or ws>=b:
                continue
            # A clipped syllable is a review item, not an invented complete word.
            if ws<a-0.001 or we>b+0.001:
                review.append({'clip_index':index,'reason':'cut_through_word','word':w['word'],'source_start':ws,'source_end':we})
                flush()
                continue
            start=x+ws-a;end=min(x+we-a,y)
            if end<=start:
                continue
            if group and (len(''.join(q['word'] for q in group)+w['word'])>max_chars or end-group[0]['start']>max_seconds or start-group[-1]['end']>.6):
                flush()
            group.append({'start':start,'end':end,'word':w['word']})
        flush()
    return {'time_basis':'output seconds','captions':captions,'review_required':review}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transcript',required=True);p.add_argument('--source-map',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args();out=Path(a.output)
    if out.suffix.lower()!='.json':raise ValueError('Output must be JSON')
    if out.exists() or out.with_suffix('.srt').exists():raise ValueError('Output exists')
    read=lambda f:json.loads(Path(f).read_text(encoding='utf-8-sig'))
    result=map_words(read(a.transcript),read(a.source_map))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    out.with_suffix('.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"],True)} --> {stamp(c["end"],True)}\n{c["text"]}' for i,c in enumerate(result['captions'])),encoding='utf-8-sig')
    print(json.dumps({'captions':len(result['captions']),'review_required':len(result['review_required'])}))


if __name__=='__main__':main()
