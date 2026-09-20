import sys,unittest
from pathlib import Path
from PIL import Image,ImageDraw,ImageStat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from scene_camera import Track,Camera,AssetTrack

def key(t,x=0,y=0,w=100,h=100,**extra):return dict(time=t,x=x,y=y,width=w,height=h,**extra)
class SceneCameraTests(unittest.TestCase):
 def test_linear(self):
  t=Track([{'time':0,'v':0,'ease':'linear'},{'time':2,'v':10}],['v']);self.assertEqual(t.at(1)['v'],5)
 def test_endpoint_clamp(self):
  t=Track([{'time':0,'v':3},{'time':1,'v':7}],['v']);self.assertEqual((t.at(-1)['v'],t.at(8)['v']),(3,7))
 def test_hold_then_switch(self):
  t=Track([{'time':0,'v':3,'ease':'hold'},{'time':1,'v':7}],['v']);self.assertEqual(t.at(.999)['v'],3);self.assertEqual(t.at(1)['v'],7)
 def test_smooth_not_linear(self):
  t=Track([{'time':0,'v':0},{'time':1,'v':1}],['v']);self.assertAlmostEqual(t.at(.25)['v'],.15625)
 def test_reject_bad_times(self):
  for rows in [[{'time':0,'v':0},{'time':0,'v':2}],[{'time':-1,'v':2}],[{'time':0,'v':float('nan')}]]:
   with self.assertRaises(ValueError):Track(rows,['v'])
 def test_reject_unknown_easing(self):
  with self.assertRaises(ValueError):Track([{'time':0,'v':2,'ease':'bounce'}],['v'])
 def test_bad_sample_time(self):
  with self.assertRaises(ValueError):Track([{'time':0,'v':2}],['v']).at(float('nan'))
 def test_aspect(self):
  with self.assertRaises(ValueError):Camera((200,200),(100,50),[key(0)])
 def test_bounds(self):
  with self.assertRaises(ValueError):Camera((200,200),(100,100),[key(0,x=150)])
 def test_view_selects_correct_region(self):
  world=Image.new('RGB',(200,100),'red');ImageDraw.Draw(world).rectangle((100,0,199,99),fill='blue')
  c=Camera(world.size,(50,50),[key(0),key(1,x=100)]);self.assertEqual(c.view(world,0).getpixel((25,25)),(255,0,0));self.assertEqual(c.view(world,1).getpixel((25,25)),(0,0,255))
 def test_return_overview(self):
  c=Camera((200,200),(100,100),[key(0,w=200,h=200),key(1,x=100,y=100),key(2,w=200,h=200)]);self.assertEqual(c.track.at(0),c.track.at(2))
 def test_projection(self):
  c=Camera((200,200),(100,100),[key(0,x=50,y=50)]);self.assertEqual(c.project((100,100),0),(50,50))
 def test_wrong_world(self):
  c=Camera((200,200),(100,100),[key(0)])
  with self.assertRaises(ValueError):c.view(Image.new('RGB',(100,100)),0)
 def test_contain_keeps_aspect(self):
  im=Image.new('RGBA',(100,100),'black');a=AssetTrack('wide',Image.new('RGB',(100,50),'red'),[key(0,opacity=1,blur=0)]);a.draw(im,0);self.assertEqual(im.getpixel((50,0)),(0,0,0,255));self.assertEqual(im.getpixel((50,50)),(255,0,0,255))
 def test_zero_opacity(self):
  im=Image.new('RGBA',(100,100),'black');before=im.tobytes();AssetTrack('zero',Image.new('RGB',(50,50),'red'),[key(0,opacity=0,blur=0)]).draw(im,0);self.assertEqual(im.tobytes(),before)
 def test_bad_opacity(self):
  with self.assertRaises(ValueError):AssetTrack('x',Image.new('RGB',(50,50)),[key(0,opacity=2,blur=0)])
 def test_missing_id(self):
  with self.assertRaises(ValueError):AssetTrack('',Image.new('RGB',(50,50)),[key(0,opacity=1,blur=0)])
 def test_blur_reduces_local_contrast(self):
  pic=Image.new('RGB',(100,100),'black');ImageDraw.Draw(pic).rectangle((50,0,99,99),fill='white')
  clear=Image.new('RGBA',(100,100));blur=clear.copy()
  AssetTrack('same',pic,[key(0,opacity=1,blur=0)]).draw(clear,0);AssetTrack('same',pic,[key(0,opacity=1,blur=8)]).draw(blur,0)
  self.assertLess(ImageStat.Stat(blur.crop((40,0,60,100))).var[0],ImageStat.Stat(clear.crop((40,0,60,100))).var[0])
if __name__=='__main__':unittest.main()
