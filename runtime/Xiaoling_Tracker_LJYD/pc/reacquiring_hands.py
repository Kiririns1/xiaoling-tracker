"""Continuous hand tracking and confirmed reacquisition; cached drawing never drives."""
import copy
import math
import time
from types import SimpleNamespace

def enhance_hand_image(rgb):
 import cv2
 lab=cv2.cvtColor(rgb,cv2.COLOR_RGB2LAB)
 lab[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(lab[:,:,0])
 return cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)

class ReacquiringHands:
 def __init__(self,primary_factory,fallback_factory,enhance=enhance_hand_image,clock=time.monotonic):
  self.primary=primary_factory();self.fallback=None;self.fallback_factory=fallback_factory
  self.enhance=enhance;self.clock=clock;self.candidate=None;self.count=0;self.last=None
  self.accepted=None;self.accepted_at=None;self.roi_hand=None
  self.overlay=[];self.overlay_at=None
 def clear_candidate(self):self.candidate=None;self.count=0;self.last=None
 def valid(self,result):
  valid=[]
  for i,hand in enumerate(result.multi_hand_landmarks or []):
   points=hand.landmark
   if len(points)!=21 or not all(math.isfinite(v) for p in points for v in (p.x,p.y,p.z)):continue
   if sum(-.1<=p.x<=1.1 and -.1<=p.y<=1.1 for p in points)<18:continue
   if math.hypot(points[0].x-points[9].x,points[0].y-points[9].y)<.025:continue
   center=tuple(sum(getattr(points[k],axis) for k in (0,5,9,13,17))/5 for axis in ('x','y'))
   valid.append((center,i,hand))
  return valid
 def finish(self,hands,labels,now):
  drawings=[]
  for hand in hands:
   drawing=copy.deepcopy(hand)
   center=lambda h:(sum(p.x for p in h.landmark)/21,sum(p.y for p in h.landmark)/21)
   c=center(hand)
   previous=min(self.overlay,key=lambda h:math.dist(c,center(h))) if self.overlay else None
   if previous is not None and self.overlay_at is not None and now-self.overlay_at<=.3 and math.dist(c,center(previous))<.15:
    for p,old in zip(drawing.landmark,previous.landmark):
     p.x=.7*p.x+.3*old.x;p.y=.7*p.y+.3*old.y;p.z=.7*p.z+.3*old.z
   drawings.append(drawing)
  held=[]
  if drawings:self.overlay=drawings;self.overlay_at=now
  elif self.overlay_at is not None and now-self.overlay_at<=.2:held=self.overlay
  return SimpleNamespace(multi_hand_landmarks=hands,multi_handedness=labels,display_hand_landmarks=drawings,held_hand_landmarks=held)
 def accept(self,valid,result,now):
  center,i,hand=min(valid,key=lambda h:math.dist(h[0],self.accepted or (.5,.5)))
  self.accepted=center;self.accepted_at=now;self.roi_hand=hand;self.clear_candidate()
  labels=result.multi_handedness or []
  return self.finish([hand],[labels[i]] if i<len(labels) else [],now)
 def crop_recovery(self,image,now):
  if self.roi_hand is None or self.accepted_at is None or now-self.accepted_at>1.:return None
  h,w=image.shape[:2];p=self.roi_hand.landmark
  xs=[q.x*w for q in p];ys=[q.y*h for q in p]
  cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
  side=max(max(xs)-min(xs),max(ys)-min(ys),min(w,h)*.22)*2.
  x0=max(0,int(cx-side/2));x1=min(w,int(cx+side/2));y0=max(0,int(cy-side/2));y1=min(h,int(cy+side/2))
  if x1-x0<32 or y1-y0<32:return None
  result=self.fallback.process(image[y0:y1,x0:x1]);mapped=[]
  for hand in result.multi_hand_landmarks or []:
   hand=copy.deepcopy(hand)
   for p in hand.landmark:p.x=(x0+p.x*(x1-x0))/w;p.y=(y0+p.y*(y1-y0))/h;p.z*=float(x1-x0)/w
   mapped.append(hand)
  return SimpleNamespace(multi_hand_landmarks=mapped,multi_handedness=result.multi_handedness or [])
 def process(self,rgb):
  now=self.clock();image=self.enhance(rgb)
  result=self.primary.process(image);valid=self.valid(result)
  if valid:return self.accept(valid,result,now)
  if self.fallback is None:self.fallback=self.fallback_factory()
  result=self.fallback.process(image);valid=self.valid(result)
  if not valid and hasattr(image,'shape'):
   cropped=self.crop_recovery(image,now)
   if cropped is not None:result=cropped;valid=self.valid(result)
  if not valid:self.clear_candidate();return self.finish([],[],now)
  center,i,hand=min(valid,key=lambda h:math.dist(h[0],self.accepted or self.candidate or (.5,.5)))
  # Already-confirmed hand can move between video and recovery graphs without
  # waiting three frames again. This was the source of repeated skeleton blanks.
  continuing=self.accepted is not None and self.accepted_at is not None and now-self.accepted_at<=.6 and math.dist(center,self.accepted)<.22
  if continuing:return self.accept([(center,i,hand)],result,now)
  stable=self.candidate is not None and self.last is not None and now-self.last<=.6 and math.dist(center,self.candidate)<.18
  self.count=self.count+1 if stable else 1;self.candidate=center;self.last=now
  if self.count<3:return self.finish([],[],now)
  return self.accept([(center,i,hand)],result,now)
 def close(self):
  self.primary.close()
  if self.fallback is not None:self.fallback.close()
