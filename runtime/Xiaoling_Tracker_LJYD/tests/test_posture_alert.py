import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from posture import metrics,classify,PostureFilter

class PostureAlertTests(unittest.TestCase):
 def points(self,dy=0,scale=1):
  p=[None]*33
  for i,xy in {0:(150,50+dy),2:(140,35+dy),5:(160,35+dy),11:(100,100),12:(200,100)}.items():
   p[i]=tuple(v*scale for v in xy)
  return p
 def test_forward_needs_both_nose_and_eyes(self):
  base=metrics(self.points(),True)
  self.assertIn('前倾',classify(metrics(self.points(20),True),base)[0])
  p=self.points();p[0]=(150,80)
  self.assertNotIn('前倾',classify(metrics(p,True),base)[0])
 def test_scale_alone_not_forward(self):
  self.assertNotIn('前倾',classify(metrics(self.points(scale=1.5),True),metrics(self.points(),True))[0])
 def test_left_right_and_normal(self):
  b=metrics(self.points(),True)
  for angle,word in ((-12,'左'),(12,'右')):
   self.assertIn('向画面'+word,classify((angle,*b[1:]),b)[0])
  self.assertIn('阈值范围',classify((4,*b[1:]),b)[0])
 def test_missing_eyes_reject_and_nan(self):
  p=self.points();p[2]=None;self.assertIsNone(metrics(p,True))
  p=self.points();p[5]=(float('nan'),0);self.assertIsNone(metrics(p,True))
 def test_hold_cooldown_recovery_missing(self):
  f=PostureFilter(hold=1,cooldown=5);f.baseline=metrics(self.points(),True)
  bad=metrics(self.points(20),True)
  self.assertFalse(f.observe(bad,0)[2]);self.assertTrue(f.observe(bad,1)[2])
  self.assertFalse(f.observe(bad,2)[2]);self.assertFalse(f.observe(None,2.1)[2])
  self.assertFalse(f.observe(bad,6)[2]);self.assertTrue(f.observe(bad,7)[2])
  for i in range(6):f.observe(f.baseline,8+i*.1)
  self.assertIsNone(f.bad_since)
 def test_five_value_calibration(self):
  f=PostureFilter();f.start_calibration(0)
  for i in range(10):f.observe(metrics(self.points(),True),i*.2)
  self.assertEqual(len(f.baseline),5)

if __name__=='__main__':unittest.main()
