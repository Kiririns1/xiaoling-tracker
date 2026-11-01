import sys,unittest,math
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from fist_gate import FistGate
from hand_geometry import fully_closed_fist
from hand_follow import HandFollower

def hand(fist=True,opened=False):return SimpleNamespace(fist=fist,open=opened,x=.5,y=.5,size=.15,label='Right')
def landmarks(extended=0):
 p=[(0.,0.,0.) for _ in range(21)]
 for i,(m,j,d,t) in enumerate(((5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20))):
  x=(i-1.5)*.25
  values=((x,1.,0.),(x,1.45,0.),(x,1.2,-.2),(x,.9,-.1))
  if i<extended:values=((x,1.,0.),(x,1.45,0.),(x,1.75,0.),(x,2.,0.))
  for k,v in zip((m,j,d,t),values):p[k]=tuple(c*.12 for c in v)
 return p
class GeometryTests(unittest.TestCase):
 def test_fully_closed_four_fingers(self):self.assertTrue(fully_closed_fist(landmarks()))
 def test_any_unclosed_finger_rejects(self):
  for count in range(1,5):self.assertFalse(fully_closed_fist(landmarks(count)))
 def test_one_partly_bent_finger_is_tolerated_when_other_three_are_closed(self):
  p=landmarks();p[7]=(-.045,.192,-.012);p[8]=(-.045,.207,-.024)
  self.assertTrue(fully_closed_fist(p))
 def test_thumb_need_not_wrap(self):
  p=landmarks();p[4]=(-.3,.2,0);self.assertTrue(fully_closed_fist(p))
 def test_tiny_and_nonfinite_reject(self):
  self.assertFalse(fully_closed_fist([tuple(v*.01 for v in p) for p in landmarks()]))
  p=landmarks();p[8]=(math.nan,0,0);self.assertFalse(fully_closed_fist(p))
class GateTests(unittest.TestCase):
 def feed(self,g,n,t,h=None,identity=1,captured=None):return g.update(h or hand(),identity,n,t if captured is None else captured,t)
 def trigger(self,g):
  result=[self.feed(g,i,i*.13) for i in range(6)]
  self.assertEqual(result,[False]*5+[True])
 def test_needs_six_unique_frames_and_elapsed_time(self):
  g=FistGate()
  for i in range(6):self.assertFalse(self.feed(g,i,i*.01))
  self.assertTrue(self.feed(g,6,.65))
 def test_not_just_elapsed_time(self):
  g=FistGate()
  self.assertFalse(self.feed(g,1,0));self.assertFalse(self.feed(g,2,.5))
 def test_duplicate_frame_never_accumulates(self):
  g=FistGate()
  for i in range(20):self.assertFalse(self.feed(g,1,i*.1))
  self.assertEqual(g.count,1)
 def test_one_ambiguous_frame_does_not_erase_real_fist_evidence(self):
  g=FistGate()
  for i in range(5):self.assertFalse(self.feed(g,i,i*.13))
  self.assertFalse(self.feed(g,5,.65,hand(False)))
  self.assertTrue(self.feed(g,6,.78))
 def test_open_palm_immediately_clears_old_evidence(self):
  g=FistGate()
  for i in range(5):self.feed(g,i,i*.13)
  self.assertFalse(self.feed(g,5,.65,hand(False,True)));self.assertEqual(g.count,0)
 def test_short_missing_detection_does_not_count_as_fist(self):
  g=FistGate()
  for i in range(5):self.feed(g,i,i*.13)
  self.assertFalse(g.update(None,None,5,.65,.65));self.assertEqual(g.count,5)
  self.assertTrue(self.feed(g,6,.78))
 def test_three_missing_frames_clear_evidence(self):
  g=FistGate()
  for i in range(5):self.feed(g,i,i*.13)
  for i in range(5,8):self.assertFalse(g.update(None,None,i,i*.13,i*.13))
  self.assertEqual(g.count,0)
 def test_evidence_window_never_triggers_without_six_real_fist_frames(self):
  g=FistGate()
  for i in range(20):
   self.assertFalse(self.feed(g,i,i*.13,hand(i%2==0)))
 def test_other_selected_hand_cannot_complete_sequence(self):
  g=FistGate()
  for i in range(5):self.assertFalse(self.feed(g,i,i*.13))
  self.assertFalse(self.feed(g,5,.65,identity=2));self.assertEqual(g.count,1)
 def test_gap_stale_and_missing_reset(self):
  for kind in ('gap','stale','missing'):
   g=FistGate()
   for i in range(5):self.feed(g,i,i*.13)
   if kind=='gap':self.assertFalse(self.feed(g,5,1.5))
   if kind=='stale':self.assertFalse(self.feed(g,5,.65,captured=-1))
   if kind=='missing':self.assertFalse(g.update(None,1,5,.65,.65))
   self.assertLessEqual(g.count,5 if kind=='missing' else 1)
 def test_held_fist_never_repeats_even_after_pause_or_loss(self):
  g=FistGate();self.trigger(g);g.pause()
  for i in range(6,100):self.assertFalse(self.feed(g,i,i*.13))
  self.assertFalse(g.armed)
 def test_requires_confirmed_open_before_second_nod(self):
  g=FistGate();self.trigger(g)
  for i in range(6,10):self.assertFalse(self.feed(g,i,i*.13,hand(False,True)))
  self.assertTrue(g.armed)
  for i in range(10,15):self.assertFalse(self.feed(g,i,i*.13))
  self.assertTrue(self.feed(g,15,15*.13))
 def test_ambiguous_nonfist_does_not_rearm(self):
  g=FistGate();self.trigger(g)
  for i in range(6,15):self.feed(g,i,i*.13,hand(False,False))
  self.assertFalse(g.armed)
 def test_only_the_follower_selected_hand_counts(self):
  f=HandFollower();a=hand(False,True);b=hand();b.x=.95
  f.update([a,b],0);self.assertIs(f.selected,a)
  f.update([],0.1);self.assertIsNone(f.selected)
if __name__=='__main__':unittest.main()
