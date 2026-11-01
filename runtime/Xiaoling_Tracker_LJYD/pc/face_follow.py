"""Face selection reuses the selected-target policy and FaceTracker steps on both axes."""
from dataclasses import dataclass
from hand_follow import HandFollower

@dataclass
class Face:
 x:float
 y:float
 size:float
 label:str='Face'

class FaceFollower(HandFollower):
 def update(self,faces,now):
  command=super().update(faces,now)
  if not faces:self.message='No face: stopped'
  self.message=self.message.replace('hand','face')
  return command  # Both axes share the unchanged FaceTracker step controller.

class TrackingModes:
 def __init__(self):self.mode='hand'
 def select(self,key):
  next_mode='hand' if key==ord('1') else 'face' if key==ord('2') else ('face' if self.mode=='hand' else 'hand') if key==ord('m') else self.mode
  changed=next_mode!=self.mode;self.mode=next_mode;return changed
