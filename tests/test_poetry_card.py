import sys,unittest
from pathlib import Path
from PIL import Image,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from poetry_card import draw_poetry
class PoetryTests(unittest.TestCase):
 def setUp(self):
  self.im=Image.new('RGBA',(600,500));self.font=ImageFont.load_default(size=24)
 def draw(self,**extra):
  kw=dict(author='Author',title='Poem title',lines=['Verse one','Verse two'],box=(20,20,550,450),heading_font=self.font,verse_font=self.font);kw.update(extra);return draw_poetry(self.im,**kw)
 def test_heading_and_lines_render_inside_the_assigned_box(self):
  boxes=self.draw();self.assertEqual(len(boxes),2);self.assertLessEqual(boxes[-1][-1],450)
  self.assertIsNotNone(self.im.getbbox());self.assertIsNone(self.im.crop((0,0,19,500)).getbbox())
 def test_tall_text_cannot_silently_clip_the_last_line(self):
  with self.assertRaises(ValueError):self.draw(box=(20,20,550,100))
 def test_long_title_cannot_silently_clip_its_name(self):
  with self.assertRaises(ValueError):self.draw(title='A very long poem title '*10)
 def test_required_attribution_and_active_line(self):
  with self.assertRaises(ValueError):self.draw(author='')
  with self.assertRaises(ValueError):self.draw(active=8)
if __name__=='__main__':unittest.main()
