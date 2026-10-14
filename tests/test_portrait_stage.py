import sys,unittest
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from portrait_stage import draw_portrait

class PortraitTests(unittest.TestCase):
    def test_cutout_does_not_fill_background(self):
        src=Image.new('RGBA',(100,200));ImageDraw.Draw(src).rectangle((30,0,70,199),fill='white')
        out=Image.new('RGBA',(500,400),'#172119')
        b=draw_portrait(out,src,(100,0,300,400),mode='cutout',shadow=False)
        self.assertEqual(b,(100,0,300,400))
        self.assertEqual(out.getpixel((105,150)),(23,33,25,255))
        self.assertEqual(out.getpixel((200,399)),(255,255,255,255))
    def test_nontransparent_frame_cannot_be_called_cutout(self):
        with self.assertRaises(ValueError):draw_portrait(Image.new('RGBA',(400,400)),Image.new('RGB',(100,100)),(0,0,300,300),mode='cutout')
    def test_frame_crop_preserves_selected_subject(self):
        src=Image.new('RGB',(300,200),'red');ImageDraw.Draw(src).rectangle((100,0,199,199),fill='blue')
        out=Image.new('RGBA',(400,300))
        draw_portrait(out,src,(100,0,200,200),crop=(100,0,200,200),shadow=False,border=0)
        self.assertEqual(out.getpixel((150,100)),(0,0,255,255))
    def test_zero_opacity_and_invalid_crop(self):
        out=Image.new('RGBA',(200,200));src=Image.new('RGB',(100,100),'white')
        draw_portrait(out,src,(20,20,180,180),opacity=0)
        self.assertIsNone(out.getbbox())
        with self.assertRaises(ValueError):draw_portrait(out,src,(20,20,180,180),crop=(0,0,101,100))

if __name__=='__main__':unittest.main()
