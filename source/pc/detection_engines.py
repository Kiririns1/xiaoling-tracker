"""Only the selected tracking graph exists; missed hands trigger automatic recovery."""
class DetectionEngines:
 def __init__(self,hand_factory,face_factory):
  self.factories={'hand':hand_factory,'face':face_factory}
  self.mode=None;self.model=None;self.misses=0;self.recoveries=0;self.restarted=False
  self.last_recovery=None
 def select(self,mode):
  if mode not in self.factories:raise ValueError('Unknown tracking mode')
  if self.mode==mode and self.model is not None:return
  self.close();self.mode=mode;self.model=self.factories[mode]()
 def process(self,mode,image,now):
  self.select(mode);self.restarted=False
  result=self.model.process(image)
  if mode=='hand':
   if result.multi_hand_landmarks:self.misses=0
   else:
    self.misses+=1
    if self.misses>=12 and (self.last_recovery is None or now-self.last_recovery>=2.):
     self.model.close();self.model=None;self.model=self.factories['hand']()
     self.misses=0;self.recoveries+=1;self.restarted=True;self.last_recovery=now
  return result
 def reset(self):self.close()
 def close(self):
  if self.model is not None:self.model.close()
  self.model=None;self.mode=None;self.misses=0;self.last_recovery=None
