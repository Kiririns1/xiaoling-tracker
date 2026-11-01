import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from hand_follow import HandFollower
from posture import PostureFilter,metrics,classify

def hand(x=.5,y=.5,label='Right'):return SimpleNamespace(x=x,y=y,size=.15,label=label,open=False)
class FollowTests(unittest.TestCase):
 def test_center_stops_both_axes(self):self.assertEqual(HandFollower().update([hand()],0),(0,0))
 def test_horizontal_undoes_mirrored_display(self):
  self.assertLess(HandFollower().update([hand(.8)],0)[0],0)
  self.assertGreater(HandFollower().update([hand(.2)],0)[0],0)
 def test_vertical_offsets_follow_in_both_directions(self):
  self.assertEqual(HandFollower().update([hand(y=.2)],0),(0.,.03))
  self.assertEqual(HandFollower().update([hand(y=.8)],0),(0.,-.03))
 def test_diagonal_and_each_axis_can_stop_independently(self):
  self.assertEqual(HandFollower().update([hand(x=.8,y=.8)],0),(-.03,-.03))
  self.assertEqual(HandFollower().update([hand(x=.5,y=.8)],0),(0.,-.03))
  self.assertEqual(HandFollower().update([hand(x=.8,y=.5)],0),(-.03,0.))
 def test_pitch_direction_can_be_reversed_without_changing_yaw(self):
  self.assertEqual(HandFollower(pitch_sign=-1).update([hand(x=.8,y=.8)],0),(-.03,.03))
 def test_vertical_offset_continues_without_triggering_an_action(self):
  f=HandFollower()
  for i in range(100):self.assertEqual(f.update([hand(y=.8)],i*.1),(0.,-.03))
 def test_not_limited_to_open_palm_or_one_handedness(self):
  for label in ('Left','Right'):self.assertNotEqual(HandFollower().update([hand(.8,label=label)],0),(0,0))
 def test_lost_hand_stops_immediately(self):
  f=HandFollower();f.update([hand(.8)],0);self.assertEqual(f.update([],.1),(0,0))
 def test_other_hand_cannot_take_over_abruptly(self):
  f=HandFollower();f.update([hand(.2)],0);self.assertEqual(f.update([hand(.8)],.1),(0,0))
 def test_steps_continue_with_fresh_hand_without_old_travel_lock(self):
  f=HandFollower()
  for i in range(100):self.assertNotEqual(f.update([hand(.8)],i*.1),(0,0))
  self.assertEqual(f.update([hand(.5)],10.1),(0,0))
 def test_distance_changes_direction_only(self):
  self.assertEqual(HandFollower().update([hand(.7)],0),HandFollower().update([hand(.95)],0))
 def test_direction_can_be_reversed(self):self.assertGreater(HandFollower(yaw_sign=-1).update([hand(.8)],0)[0],0)

class RestoredPostureTests(unittest.TestCase):
 def points(self,nose=(150,50),a=(100,100),b=(200,100)):
  p=[None]*33;p[0]=nose;p[11]=a;p[12]=b;return p
 def calibrated(self):
  f=PostureFilter();f.start_calibration(0)
  for i in range(10):f.observe(metrics(self.points()),i*.2)
  self.assertIsNotNone(f.baseline);return f
 def test_multiframe_calibration_and_normal(self):
  f=self.calibrated();self.assertIn('阈值范围',f.observe(metrics(self.points()),2)[0])
 def test_left_right_and_shoulder_tilt(self):
  f=self.calibrated()
  self.assertIn('左偏',classify(metrics(self.points(nose=(110,50))),f.baseline)[0])
  self.assertIn('右偏',classify(metrics(self.points(nose=(190,50))),f.baseline)[0])
  self.assertIn('肩线倾斜',classify(metrics(self.points(a=(100,80),b=(200,120))),f.baseline)[0])
 def test_missing_points_do_not_raise_alert(self):
  f=self.calibrated();self.assertFalse(f.observe(None,2)[2]);self.assertIsNone(f.bad_since)
 def test_camera_move_invalidates_calibration(self):
  f=self.calibrated();f.reset();self.assertIsNone(f.baseline);self.assertFalse(f.observe(metrics(self.points()),3)[2])

if __name__=='__main__':unittest.main()
