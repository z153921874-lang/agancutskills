import sys,unittest
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from portrait_stage import draw_portrait,frame_geometry

class SafetyTests(unittest.TestCase):
 def test_tall_frame_preserves_both_source_edges(self):
  src=Image.new('RGB',(400,200),'black');d=ImageDraw.Draw(src);d.rectangle((0,0,39,199),fill='red');d.rectangle((360,0,399,199),fill='blue')
  out=Image.new('RGBA',(200,400));bounds=draw_portrait(out,src,(0,0,200,400),shadow=False,border=0,radius=0)
  self.assertEqual(bounds,(0,150,200,250));self.assertEqual(out.getpixel((5,200))[:3],(255,0,0));self.assertEqual(out.getpixel((195,200))[:3],(0,0,255))
 def test_cover_cannot_hide_a_head_near_top(self):
  src=Image.new('RGB',(200,400));out=Image.new('RGBA',(400,200))
  with self.assertRaises(ValueError):draw_portrait(out,src,(0,0,400,200),fit='cover',protected=(70,0,130,70))
  draw_portrait(out,src,(0,0,400,200),fit='contain',protected=(70,0,130,70))
 def test_geometry_reports_wide_shot_loss(self):
  g=frame_geometry((1144,720),(0,0,480,520),crop=(300,35,850,635),fit='cover')
  self.assertGreater(g['visible_source'][1],35);self.assertAlmostEqual(g['scale'],480/550)
 def test_protected_coordinates_are_source_coordinates(self):
  out=Image.new('RGBA',(300,300));src=Image.new('RGB',(1000,800))
  draw_portrait(out,src,(10,10,290,290),crop=(400,100,900,650),protected=(500,150,850,600),shadow=False)
  with self.assertRaises(ValueError):draw_portrait(out,src,(10,10,290,290),crop=(400,100,900,650),protected=(100,150,850,600))
if __name__=='__main__':unittest.main()
