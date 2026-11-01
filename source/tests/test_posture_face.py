import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from posture_face import pose_face,PostureFaceFollower
from face_follow import Face
from posture_config import FACE_TARGET_Y

class PostureFaceTests(unittest.TestCase):
 def test_face_uses_same_pose_landmarks(self):
  p=[None]*33;p[0]=(160,90);p[2]=(145,75);p[5]=(175,75)
  f=pose_face(p,320,240)
  self.assertEqual(f.x,.5);self.assertAlmostEqual(f.y,1/3)
 def test_missing_or_invalid_face_stops(self):
  self.assertIsNone(pose_face([None]*33,320,240))
  p=[None]*33;p[0]=(float('nan'),90);p[2]=(145,75);p[5]=(175,75)
  self.assertIsNone(pose_face(p,320,240))
  f=PostureFaceFollower();f.update([Face(.8,.6,.15)],0)
  self.assertEqual(f.update([],0.1),(0,0))
 def test_target_keeps_room_for_shoulders(self):
  self.assertEqual(PostureFaceFollower().update([Face(.5,FACE_TARGET_Y,.15)],0),(0,0))
 def test_dual_axis_follow(self):
  yaw,pitch=PostureFaceFollower().update([Face(.8,.7,.15)],0)
  self.assertLess(yaw,0);self.assertLess(pitch,0)

if __name__=='__main__':unittest.main()
