import sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/talking-head-editor/scripts'))
from editorial_materials import make_plate,draw_plate,overlap_fraction,surface

class MaterialsTests(unittest.TestCase):
    def test_contain_keeps_wide_source_complete(self):
        src=Image.new('RGBA',(400,100),'white')
        src.putpixel((0,50),(255,0,0,255));src.putpixel((399,50),(0,0,255,255))
        p=make_plate('test',src,(414,214),border=7)
        x,y,x2,y2=p.content_box
        self.assertEqual((x2-x,y2-y),(400,100))
        self.assertEqual(p.image.getpixel((x,y+50)),(255,0,0,255))
        self.assertEqual(p.image.getpixel((x2-1,y+50)),(0,0,255,255))

    def test_rotated_shadow_plate_stays_transparent_outside(self):
        p=make_plate('test',Image.new('RGB',(200,100),'white'),(214,114))
        out=Image.new('RGBA',(500,400))
        box=draw_plate(out,p,(250,200),angle=8)
        self.assertEqual(out.getpixel((0,0))[3],0)
        self.assertGreater(box[2]-box[0],214)
        self.assertGreater(out.getpixel((250,200))[3],240)

    def test_path_intersection_uses_protected_area(self):
        self.assertEqual(overlap_fraction((0,0,100,100),(200,200,300,300)),0)
        self.assertEqual(overlap_fraction((250,200,350,300),(200,200,300,300)),.5)

    def test_background_is_temporally_stable(self):
        self.assertEqual(surface((120,90),seed=4).tobytes(),surface((120,90),seed=4).tobytes())

if __name__=='__main__':unittest.main()
