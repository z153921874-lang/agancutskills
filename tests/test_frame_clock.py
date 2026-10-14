import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from frame_clock import frame_at,before,contains
class ClockTests(unittest.TestCase):
 def test_decimal_matte_endpoint_belongs_only_to_next_scene(self):
  t=63.4+311/30
  self.assertFalse(contains(t,63.4,73.766667,30));self.assertTrue(contains(t,73.766667,77.733333,30));self.assertFalse(before(t,73.766667,30))
 def test_consecutive_spans_cover_each_frame_exactly_once(self):
  spans=[(0,63.4),(63.4,73.766667),(73.766667,77.733333),(77.733333,88),(88,187.4)]
  for n in range(5622):self.assertEqual(sum(contains(n/30,a,b,30) for a,b in spans),1,n)
 def test_rate_is_declared_for_other_frame_grids(self):
  self.assertEqual(frame_at(.12,25),3);self.assertEqual(frame_at(.12,30),4)
 def test_invalid_grid_and_empty_span(self):
  with self.assertRaises(ValueError):frame_at(1,0)
  with self.assertRaises(ValueError):frame_at(float('nan'),30)
  with self.assertRaises(ValueError):contains(0,1,1,30)
if __name__=='__main__':unittest.main()
