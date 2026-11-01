import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from detection_engines import DetectionEngines
class EngineTests(unittest.TestCase):
 def setup_engines(self,detected=False):
  events=[];models=[]
  class Model:
   def __init__(self,kind):self.kind=kind;self.closed=False;events.append(('create',kind));models.append(self)
   def process(self,image):
    assert not self.closed;events.append(('process',self.kind))
    return SimpleNamespace(multi_hand_landmarks=[object()] if detected else [],detections=[])
   def close(self):self.closed=True;events.append(('close',self.kind))
  return DetectionEngines(lambda:Model('hand'),lambda:Model('face')),events,models
 def test_hand_mode_never_creates_or_calls_face_detector(self):
  d,e,_=self.setup_engines(True)
  for i in range(10):d.process('hand',None,i*.1)
  self.assertTrue(all(kind=='hand' for _,kind in e));d.close()
 def test_face_mode_never_creates_or_calls_hand_detector(self):
  d,e,_=self.setup_engines()
  for i in range(10):d.process('face',None,i*.1)
  self.assertTrue(all(kind=='face' for _,kind in e));d.close()
 def test_switch_closes_old_graph_before_creating_other(self):
  d,e,m=self.setup_engines();d.process('hand',None,0);d.select('face')
  self.assertEqual(e[-2:],[('close','hand'),('create','face')]);self.assertTrue(m[0].closed)
  d.process('face',None,.1);d.select('hand');self.assertTrue(m[1].closed);d.close()
 def test_twelve_misses_automatically_recreate_hand_graph(self):
  d,e,m=self.setup_engines()
  for i in range(12):d.process('hand',None,i*.1)
  self.assertTrue(m[0].closed);self.assertEqual(d.recoveries,1);self.assertTrue(d.restarted)
  self.assertEqual(len(m),2);d.close()
 def test_recovery_is_rate_limited_while_no_hand_visible(self):
  d,e,m=self.setup_engines()
  for i in range(30):d.process('hand',None,i*.1)
  self.assertEqual(d.recoveries,1);d.process('hand',None,3.3);self.assertEqual(d.recoveries,2);d.close()
 def test_detected_hand_clears_miss_counter(self):
  d,e,m=self.setup_engines(True);d.misses=2;d.process('hand',None,0)
  self.assertEqual(d.misses,0);self.assertFalse(d.restarted);d.close()
 def test_same_mode_does_not_create_duplicate_graphs(self):
  d,e,m=self.setup_engines(True);d.select('hand');d.select('hand');self.assertEqual(len(m),1);d.close()
 def test_reset_and_close_release_graph_without_recreating(self):
  d,e,m=self.setup_engines();d.select('face');d.reset();self.assertTrue(m[0].closed);self.assertIsNone(d.model)
  d.close();self.assertEqual(len(m),1)
if __name__=='__main__':unittest.main()
