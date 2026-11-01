import sys,unittest
from pathlib import Path
from types import SimpleNamespace as S
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from reacquiring_hands import ReacquiringHands

def result(found=True):
 points=[S(x=.35+(i%5)*.04,y=.3+(i//5)*.05,z=0) for i in range(21)]
 return S(multi_hand_landmarks=[S(landmark=points)] if found else [],multi_handedness=[])
class ReacquisitionTests(unittest.TestCase):
 def setup_model(self,normal=False):
  events=[];times=iter(i*.1 for i in range(100))
  class Model:
   def __init__(self,kind):self.kind=kind;self.closed=False;events.append(('create',kind))
   def process(self,image):events.append(('process',self.kind));return result(normal if self.kind=='normal' else True)
   def close(self):self.closed=True;events.append(('close',self.kind))
  return ReacquiringHands(lambda:Model('normal'),lambda:Model('fallback'),lambda x:x,lambda:next(times)),events
 def test_normal_detection_never_initializes_fallback(self):
  m,e=self.setup_model(True);self.assertTrue(m.process(None).multi_hand_landmarks)
  self.assertNotIn(('create','fallback'),e);m.close()
 def test_fallback_needs_three_stable_frames(self):
  m,e=self.setup_model()
  self.assertFalse(m.process(None).multi_hand_landmarks);self.assertFalse(m.process(None).multi_hand_landmarks)
  self.assertTrue(m.process(None).multi_hand_landmarks);m.close()
 def test_missing_or_invalid_landmarks_cannot_restore_motion(self):
  m,e=self.setup_model();m.process(None);m.fallback.process=lambda image:result(False)
  self.assertFalse(m.process(None).multi_hand_landmarks);self.assertEqual(m.count,0);m.close()
 def test_close_releases_both_hand_graphs(self):
  m,e=self.setup_model();m.process(None);m.close()
  self.assertIn(('close','normal'),e);self.assertIn(('close','fallback'),e)
 def test_primary_hit_does_not_force_three_frame_wait_on_next_fallback(self):
  m,e=self.setup_model();m.primary.process=lambda image:result(True)
  self.assertTrue(m.process(None).multi_hand_landmarks)
  m.primary.process=lambda image:result(False)
  self.assertTrue(m.process(None).multi_hand_landmarks);m.close()
 def test_recovered_hand_remains_visible_on_each_new_fallback_result(self):
  m,e=self.setup_model()
  for i in range(2):self.assertFalse(m.process(None).multi_hand_landmarks)
  for i in range(8):self.assertTrue(m.process(None).multi_hand_landmarks)
  m.close()
 def test_held_skeleton_is_display_only_and_not_a_detection(self):
  m,e=self.setup_model(True);m.process(None)
  m.primary.process=lambda image:result(False)
  m.fallback_factory=lambda:type('Empty',(),{'process':lambda self,image:result(False),'close':lambda self:None})()
  r=m.process(None)
  self.assertFalse(r.multi_hand_landmarks);self.assertTrue(r.held_hand_landmarks);m.close()
if __name__=='__main__':unittest.main()
