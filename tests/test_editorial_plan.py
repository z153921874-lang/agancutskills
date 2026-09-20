import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts/plan_editorial.py'
spec=importlib.util.spec_from_file_location('editorial',SCRIPT);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def fixture():
    mapping=[{'source':'input.mp4','source_start':10,'source_end':12,'output_start':0,'output_end':2},
             {'source':'input.mp4','source_start':20,'source_end':22,'output_start':2,'output_end':4}]
    scenes=[{'id':'first','start':0,'end':2,'role':'metaphor','takeaway':'建立比喻','focus':'主体','entry':'直接切入','exit':'回到新状态','assets':['same']},
            {'id':'second','start':2,'end':4,'role':'comparison','takeaway':'比较前后状态','focus':'新状态','entry':'旧主体退后','exit':'结束','assets':['same'],'callback':{'scene':'first','new_meaning':'旧对象参与新状态比较'}}]
    cues=[{'id':'one','scene':'first','clip_index':0,'source_start':10.13,'source_end':10.6,'text':'重点','timing_basis':'word_verified','evidence':'人工核对词开始与结束','hold':.8}]
    return {'fps':25,'duration':4,'scenes':scenes,'cues':cues},mapping

class PlanTests(unittest.TestCase):
    def setUp(self):self.p,self.m=fixture()
    def run_plan(self):return mod.analyze(self.p,self.m)
    def test_source_mapping_ceil_never_precedes_word(self):
        c=self.run_plan()['cues'][0];self.assertEqual(c['start'],.16);self.assertEqual(c['end'],.96)
    def test_reordered_source_maps_correctly(self):
        self.p['cues'][0].update(scene='second',clip_index=1,source_start=20.13,source_end=20.6)
        self.assertEqual(self.run_plan()['cues'][0]['start'],2.16)
    def test_repeated_source_requires_explicit_clip(self):
        self.m[1].update(source_start=10,source_end=12);self.p['cues'][0].update(scene='second',clip_index=1)
        self.assertEqual(self.run_plan()['cues'][0]['start'],2.16)
    def test_deleted_words_rejected(self):
        self.p['cues'][0].update(source_start=13,source_end=14)
        with self.assertRaises(ValueError):self.run_plan()
    def test_cross_cut_word_rejected(self):
        self.p['cues'][0].update(source_start=11.8,source_end=12.2)
        with self.assertRaises(ValueError):self.run_plan()
    def test_hold_clipped_and_flagged(self):
        self.p['cues'][0].update(source_start=11.8,source_end=11.96)
        r=self.run_plan();self.assertEqual(r['cues'][0]['end'],2);self.assertIn('short_hold',[w['code'] for w in r['warnings']])
    def test_lead_flagged(self):
        self.p['cues'][0].update(source_start=10.5,source_end=11,lead=.2)
        self.assertIn('early_cue',[w['code'] for w in self.run_plan()['warnings']])
    def test_asr_remains_unverified(self):
        self.p['cues'][0]['timing_basis']='asr_unverified';r=self.run_plan()
        self.assertIn('timing_review',[w['code'] for w in r['warnings']]);self.assertEqual(r['review_status'],'pending')
    def test_scene_gap_rejected(self):
        self.p['scenes'][1]['start']=2.04
        with self.assertRaises(ValueError):self.run_plan()
    def test_scene_overlap_rejected(self):
        self.p['scenes'][1]['start']=1.96
        with self.assertRaises(ValueError):self.run_plan()
    def test_future_callback_rejected(self):
        self.p['scenes'][0]['callback']={'scene':'second','new_meaning':'错误未来引用'}
        with self.assertRaises(ValueError):self.run_plan()
    def test_callback_identity_warned(self):
        self.p['scenes'][1]['assets']=['different'];self.assertIn('callback_identity',[w['code'] for w in self.run_plan()['warnings']])
    def test_speed_change_rejected(self):
        self.m[0]['source_end']=14
        with self.assertRaises(ValueError):self.run_plan()
    def test_nonfinite_rejected(self):
        self.p['cues'][0]['source_start']=float('nan')
        with self.assertRaises(ValueError):self.run_plan()
    def test_unknown_timing_basis_rejected(self):
        self.p['cues'][0]['timing_basis']='automatic_perfect'
        with self.assertRaises(ValueError):self.run_plan()
    def test_whole_review_and_each_cut_present(self):
        q=self.run_plan()['review_queue'];self.assertEqual(len([r for r in q if r['kind']=='listening']),1)
        self.assertEqual(q[-1]['end'],4);self.assertTrue(all(r['status']=='pending' for r in q))
    def test_html_transcript_cannot_inject_script(self):
        self.p['cues'][0]['text']='</script><script>alert(1)</script>'
        page=mod.review_html(self.run_plan(),Path('demo.mp4'))
        self.assertNotIn('</script><script>alert(1)',page);self.assertIn('\\u003c/script>',page)
    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'p.json';m=root/'m.json';out=root/'result'
            p.write_text(json.dumps(self.p));m.write_text(json.dumps(self.m))
            cmd=[sys.executable,str(SCRIPT),'--plan',str(p),'--source-map',str(m),'--output-dir',str(out)]
            first=subprocess.run(cmd,capture_output=True);self.assertEqual(first.returncode,0,first.stderr)
            before=(out/'review.json').read_bytes();second=subprocess.run(cmd,capture_output=True)
            self.assertNotEqual(second.returncode,0);self.assertEqual(before,(out/'review.json').read_bytes())
    def test_duplicate_cue_rejected(self):
        self.p['cues'].append(copy.deepcopy(self.p['cues'][0]))
        with self.assertRaises(ValueError):self.run_plan()
    def test_non_grid_scene_rejected(self):
        self.p['scenes'][0]['end']=2.01;self.p['scenes'][1]['start']=2.01
        with self.assertRaises(ValueError):self.run_plan()
    def test_duration_disagreement_rejected(self):
        self.p['duration']=5
        with self.assertRaises(ValueError):self.run_plan()
    def test_overlap_warned_not_silently_combined(self):
        c=copy.deepcopy(self.p['cues'][0]);c['id']='other';self.p['cues'].append(c)
        self.assertIn('emphasis_overlap',[w['code'] for w in self.run_plan()['warnings']])

if __name__=='__main__':unittest.main()
