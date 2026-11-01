"""Six real fist observations in eight fresh frames, with brief miss tolerance."""
from collections import deque
class FistGate:
 MIN_FRAMES=6
 MIN_HOLD=.6
 MAX_GAP=.6
 OPEN_FRAMES=4
 OPEN_HOLD=.3
 def __init__(self):
  self.armed=True;self.last_frame=None;self.last_time=None;self.identity=None
  self.samples=deque(maxlen=8);self.count=0;self.since=None;self.open_count=0;self.open_since=None
  self.confirmation=(0,0);self.message='';self.missing=0
 def pause(self):
  self.samples.clear();self.count=0;self.since=None;self.open_count=0;self.open_since=None
  self.last_time=None;self.identity=None;self.missing=0
 def update(self,hand,identity,frame_id,captured,now):
  if frame_id==self.last_frame:return False
  self.last_frame=frame_id
  if frame_id is None or now-captured<0 or now-captured>.7:
   self.pause();self.message='';return False
  if self.last_time is not None and now-self.last_time>self.MAX_GAP:self.pause()
  if hand is None:
   self.missing+=1;self.open_count=0;self.open_since=None
   self.samples.append((now,False))
   if self.missing>2:self.pause()
   self.count=sum(v for _,v in self.samples)
   self.message='Hand briefly lost: fist confirmation paused' if self.count else ''
   return False
  if self.identity is not None and identity!=self.identity:self.pause()
  self.identity=identity;self.last_time=now;self.missing=0
  opened=getattr(hand,'open',False) and not getattr(hand,'fist',False)
  if not self.armed:
   if opened:
    if not self.open_count:self.open_since=now
    self.open_count+=1
    if self.open_count>=self.OPEN_FRAMES and now-self.open_since+1e-9>=self.OPEN_HOLD:
     self.armed=True;self.open_count=0;self.open_since=None;self.samples.clear()
   else:self.open_count=0;self.open_since=None
   self.message='' if self.armed else 'Fist action used: fully open hand to rearm'
   return False
  if opened:self.samples.clear()
  closed=getattr(hand,'fist',False)
  self.samples.append((now,closed));positive=[t for t,v in self.samples if v]
  self.count=len(positive);self.since=positive[0] if positive else None
  if not positive:self.message='';return False
  held=now-positive[0];self.message=f'Fist evidence {self.count}/6 in 8 frames | {held:.1f}s'
  if closed and self.count>=self.MIN_FRAMES and held+1e-9>=self.MIN_HOLD:
   self.confirmation=(self.count,max(600,int(round(held*1000))))
   self.armed=False;self.samples.clear();self.count=0;self.since=None;self.message='Fist confirmed: one slow nod'
   return True
  return False
