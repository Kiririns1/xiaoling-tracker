"""Additional number gesture gate; existing tracking/fist geometry is unchanged."""
import math
from hand_geometry import angle, distance

def number_gesture(points, aspect=1.):
    if len(points)!=21 or not all(math.isfinite(v) for p in points for v in p):return None
    p=[(q[0]*aspect,q[1],0.) for q in points]
    palm=distance(p[0],p[9])
    if palm<.035 or distance(p[5],p[17])<.025:return None
    extended=[]
    for m,j,d,t in ((5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)):
        ratio=distance(p[t],p[0])/max(distance(p[j],p[0]),1e-8)
        reach=distance(p[t],p[m])/palm
        straight=angle(p[m],p[j],p[d])>155 and angle(p[j],p[d],p[t])>150 and ratio>1.12
        folded=ratio<1.12 and reach<1.05
        if not straight and not folded:return None
        extended.append(straight)
    # Standard counting: index, index+middle, +ring, all four; thumb tucked.
    if distance(p[4],p[5])>palm*.85:return None
    for n in range(1,5):
        if extended==[True]*n+[False]*(4-n):return n
    return None

class NumberGate:
    def __init__(self):self.reset();self.last_frame=None
    def reset(self):self.candidate=None;self.since=0;self.count=0;self.last_time=None;self.sent=None
    def update(self,number,identity,frame_id,captured,now):
        if frame_id==self.last_frame:return None
        self.last_frame=frame_id
        if frame_id is None or not 0<=now-captured<=.7 or number not in (1,2,3,4):
            self.reset();return None
        key=(identity,number)
        if key!=self.candidate or self.last_time is None or now-self.last_time>.6:
            self.reset();self.candidate=key;self.since=now
        self.last_time=now;self.count+=1
        if self.count>=6 and now-self.since>=.6 and self.sent!=key:
            self.sent=key;return number*25
        return None
