import json,sys,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from hand_link import HandLink
from esp_transport import ESPTransport

class VoiceModeLinkTests(unittest.TestCase):
    def test_mode_change_uses_observed_revision_and_clears_motion(self):
        posted=[];polled=threading.Event();configured=threading.Event()
        class Client:
            def __init__(self,**kwargs):pass
            def close(self):pass
            def request(self,url,data=None):
                if data is not None:
                    posted.append(json.loads(data));configured.set()
                    return 200,{},b'{"accepted":true}'
                polled.set()
                state={'mode':'gesture_step','boot_id':1,'revision':9,'tracking_revision':3,
                       'hand_follow_style':'facetracker-dual-step-v1','hand_follow_axes':'yaw_pitch'}
                return 200,{},json.dumps(state).encode()
        with patch('hand_link.LANClient',Client):
            link=HandLink('http://device:81',ESPTransport());link.thread.start()
            try:
                self.assertTrue(polled.wait(1))
                deadline=time.monotonic()+1
                while not link.snapshot()[0] and time.monotonic()<deadline:time.sleep(.005)
                link.target(.03,0,1,time.monotonic())
                link.configure('face',True)
                self.assertTrue(configured.wait(1))
            finally:link.close()
        configs=[p for p in posted if p.get('action')=='track_face']
        self.assertEqual(configs,[{'action':'track_face','expected_tracking_revision':3}])
        self.assertIsNone(link.nod_pending)

if __name__=='__main__':unittest.main()
