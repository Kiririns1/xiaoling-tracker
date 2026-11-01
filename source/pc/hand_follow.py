"""Follow the selected hand with identical independent horizontal/vertical steps."""
import math

class HandFollower:
 def __init__(self,yaw_sign=1,pitch_sign=1):
  self.yaw_sign=yaw_sign;self.pitch_sign=pitch_sign;self.reset()
 def reset(self):
  self.target=None;self.seen=0;self.selected=None;self.track_id=getattr(self,'track_id',0)+1;self.message='Show either hand'
 def update(self,hands,now):
  self.selected=None
  if not hands:
   if now-self.seen>.6:self.target=None
   self.message='No hand: stopped';return 0.,0.
  if self.target is None or now-self.seen>.6:
   hand=min(hands,key=lambda h:(h.x-.5)**2+(h.y-.5)**2);self.track_id+=1
  else:
   hand=min(hands,key=lambda h:(h.x-self.target[0])**2+(h.y-self.target[1])**2)
   if math.hypot(hand.x-self.target[0],hand.y-self.target[1])>max(.28,min(.45,hand.size*2.5)):
    self.message='Selected hand lost: stopped';return 0.,0.
  self.selected=hand;self.target=(hand.x,hand.y);self.seen=now
  def direction(position,sign):
   error=position-.5
   return 0. if abs(error)<.14 else -sign*.03*(1 if error>0 else -1)
  # X undoes mirrored display; image Y grows downward, positive pitch moves up.
  yaw=direction(hand.x,self.yaw_sign);pitch=direction(hand.y,self.pitch_sign)
  self.message=f'{hand.label} FaceTracker steps | yaw {yaw:+.2f} pitch {pitch:+.2f}' if yaw or pitch else f'{hand.label} centered'
  return yaw,pitch
