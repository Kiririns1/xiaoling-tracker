import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from face_follow import Face,FaceFollower,TrackingModes
from hand_geometry import fully_closed_fist
from test_fist import landmarks
class ModeTests(unittest.TestCase):
 def test_keys_select_and_toggle_modes(self):
  m=TrackingModes();self.assertEqual(m.mode,'hand');self.assertTrue(m.select(ord('2')));self.assertEqual(m.mode,'face')
  self.assertFalse(m.select(ord('2')));self.assertTrue(m.select(ord('1')));self.assertTrue(m.select(ord('m')));self.assertEqual(m.mode,'face')
 def test_unrelated_keys_do_not_switch(self):
  m=TrackingModes()
  for k in (ord('x'),ord('y'),32,ord('f'),ord('q')):self.assertFalse(m.select(k))
 def test_face_duplicates_original_yaw_logic_on_pitch(self):
  self.assertEqual(FaceFollower().update([Face(.8,.8,.3)],0),(-.03,-.03))
  self.assertEqual(FaceFollower().update([Face(.2,.2,.3)],0),(.03,.03))
  self.assertEqual(FaceFollower().update([Face(.5,.8,.3)],0),(0.,-.03))
 def test_face_loss_stops_and_other_face_cannot_jump_in(self):
  f=FaceFollower();f.update([Face(.2,.5,.1)],0)
  self.assertEqual(f.update([Face(.9,.5,.1)],.1),(0.,0.));self.assertEqual(f.update([],.2),(0.,0.))
 def test_relaxed_fist_accepts_straight_distal_joint_and_noisy_depth(self):
  p=landmarks()
  p[7]=(p[7][0],p[7][1],.2);p[8]=(p[8][0],p[8][1],.3)
  self.assertTrue(fully_closed_fist(p))
if __name__=='__main__':unittest.main()
