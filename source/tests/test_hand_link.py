import sys
import json
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from hand_link import HandLink
from esp_transport import ESPTransport

class HandLinkTests(unittest.TestCase):
 def setup_link(self,supported=True,fail=False):
  records=[];posted=threading.Event()
  class Client:
   def __init__(self,**kw):pass
   def request(self,url,data=None):
    if data is not None:
     records.append(json.loads(data));posted.set()
     if fail:raise TimeoutError('unknown result')
     return (202 if url.endswith('/api/fist-nod') else 200),{},b'{"accepted":true}'
    return 200,{},json.dumps({'mode':'gesture_step','fist_nod_supported':supported,'hand_follow_supported':supported,'hand_follow_style':'facetracker-dual-step-v1' if supported else None,'hand_follow_axes':'yaw_pitch' if supported else None,'boot_id':123,'revision':7,'ready':True}).encode()
   def close(self):pass
  return Client,records,posted
 def wait_state(self,link):
  end=time.monotonic()+1
  while not link.snapshot()[1] and time.monotonic()<end:time.sleep(.01)
  self.assertTrue(link.snapshot()[1])
 def test_old_board_never_receives_follow_motion(self):
  client,records,_=self.setup_link(False)
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:self.wait_state(link);link.target(.03,-.02,12,time.monotonic());time.sleep(.1);self.assertEqual(records,[]);self.assertIn('Upload',link.snapshot()[2])
   finally:link.close()
 def test_dual_axis_command_preserves_pitch_and_exit_stops_both(self):
  client,records,posted=self.setup_link()
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:
    self.wait_state(link);link.target(.03,-.02,12,time.monotonic());self.assertTrue(posted.wait(1))
    self.assertEqual((records[0]['yaw'],records[0]['pitch']),(.03,-.02));self.assertEqual(records[0]['frame_id'],12)
   finally:link.close()
   self.assertEqual((records[-1]['yaw'],records[-1]['pitch']),(0,0));self.assertGreater(records[-1]['seq'],records[0]['seq'])
 def test_stale_motion_is_not_sent(self):
  client,records,_=self.setup_link()
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:self.wait_state(link);link.target(.03,0,12,time.monotonic()-2);time.sleep(.1);self.assertEqual(records,[])
   finally:link.close()
 def test_unknown_motion_result_is_not_replayed(self):
  client,records,posted=self.setup_link(fail=True)
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:self.wait_state(link);link.target(.03,0,12,time.monotonic());self.assertTrue(posted.wait(1));time.sleep(.15);self.assertEqual(len(records),1)
   finally:link.close()
 def test_space_stop_uses_full_stop_endpoint(self):
  client,records,posted=self.setup_link()
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:
    self.wait_state(link);link.stop_all();self.assertTrue(posted.wait(1));self.assertEqual(records[0],{'action':'stop'})
   finally:link.close()
 def test_fist_nod_is_one_shot_with_confirmation_evidence(self):
  client,records,posted=self.setup_link()
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:
    self.wait_state(link);link.nod(12,time.monotonic(),6,650);self.assertTrue(posted.wait(1));time.sleep(.1)
    self.assertEqual(len(records),1);self.assertEqual(records[0]['confirmed_frames'],6);self.assertEqual(records[0]['held_ms'],650)
   finally:link.close()
 def test_unknown_nod_result_is_not_retried(self):
  client,records,posted=self.setup_link(fail=True)
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:
    self.wait_state(link);link.nod(12,time.monotonic(),6,650);self.assertTrue(posted.wait(1));time.sleep(.15)
    self.assertEqual(len(records),1)
   finally:link.close()
 def test_stale_nod_is_discarded(self):
  client,records,_=self.setup_link()
  with patch('hand_link.LANClient',client):
   link=HandLink('http://test',ESPTransport(False));link.thread.start()
   try:self.wait_state(link);link.nod(12,time.monotonic()-2,6,650);time.sleep(.1);self.assertEqual(records,[])
   finally:link.close()
if __name__=='__main__':unittest.main()
