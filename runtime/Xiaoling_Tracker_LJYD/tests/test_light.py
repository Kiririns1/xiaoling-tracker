import sys, unittest, json, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from light_gesture import NumberGate, number_gesture
from light_link import LightLink
from esp_transport import ESPTransport
from test_fist import landmarks

class LightTests(unittest.TestCase):
    def test_number_geometry_and_fist(self):
        for n in range(1,5):
            p=landmarks(n);p[4]=p[5]
            self.assertEqual(number_gesture(p),n)
        self.assertIsNone(number_gesture(landmarks()))
    def test_open_thumb_rejects_five(self):
        p=landmarks(4);p[4]=(-.4,.1,0)
        self.assertIsNone(number_gesture(p))
    def test_stability_single_event_and_changed_level(self):
        g=NumberGate()
        results=[g.update(2,1,i,i*.13,i*.13) for i in range(20)]
        self.assertEqual([x for x in results if x is not None],[50])
        results=[g.update(4,1,i,i*.13,i*.13) for i in range(20,30)]
        self.assertEqual([x for x in results if x is not None],[100])
    def test_duplicate_stale_identity_and_missing(self):
        g=NumberGate()
        for i in range(10):self.assertIsNone(g.update(1,1,1,0,i*.1))
        self.assertIsNone(g.update(1,1,2,0,2))
        for i in range(5):self.assertIsNone(g.update(1,1,i+3,3+i*.13,3+i*.13))
        self.assertIsNone(g.update(1,2,10,3.8,3.8))
        self.assertIsNone(g.update(None,2,11,3.9,3.9))
    def test_failed_toggle_not_retried(self):
        calls=[]
        class Client:
            def __init__(self,**kwargs):pass
            def request(self,url,data):calls.append(json.loads(data));raise TimeoutError()
            def close(self):pass
        with patch('light_link.LANClient',Client):
            link=LightLink('http://device',ESPTransport());link.thread.start()
            link.send('toggle',123)
            deadline=time.monotonic()+1
            while not calls and time.monotonic()<deadline:time.sleep(.01)
            link.close()
        self.assertEqual(len(calls),1);self.assertEqual(calls[0]['boot_id'],123)

if __name__=='__main__':unittest.main()
