"""MediaPipe palm geometry. Openness is diagnostic, not a follow prerequisite."""
from collections import deque
from dataclasses import dataclass
import math

def distance(a,b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
def angle(a,b,c):
    u=[a[i]-b[i] for i in range(3)];v=[c[i]-b[i] for i in range(3)]
    n=math.sqrt(sum(x*x for x in u)*sum(x*x for x in v))
    return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/n)))) if n>1e-8 else 0

@dataclass
class Hand:
    label: str
    x: float
    y: float
    size: float
    angle: float
    open: bool
    fist: bool=False

def fully_closed_fist(p):
    """Tolerate depth/occlusion noise; reject clearly extended fingers.

    Thumb is unrestricted. Three fingers must be clearly folded, and the fourth
    must not be straight. Temporal confirmation uses six real observations in eight fresh frames / 0.6 seconds.
    """
    if len(p)!=21 or not all(math.isfinite(v) for q in p for v in q):return False
    p=[(q[0],q[1],0.) for q in p]  # Image geometry avoids noisy inferred depth.
    palm=distance(p[0],p[9])
    if palm<.035 or distance(p[5],p[17])<.025:return False
    curled=0
    for mcp,pip,dip,tip in ((5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)):
        bend=angle(p[mcp],p[pip],p[dip]);distal=angle(p[pip],p[dip],p[tip])
        ratio=distance(p[tip],p[0])/max(1e-8,distance(p[pip],p[0]))
        reach=distance(p[tip],p[mcp])/palm
        # A clearly extended finger rejects the fist. Short projected fingers
        # may have unreliable angles, so use multiple independent curl cues.
        if ratio>1.25 and reach>.8:return False
        if bend>165 and distal>155 and reach>.9:return False
        compact=reach<1.05 and ratio<1.2
        returned=ratio<1.03
        folded=bend<150 or distal<140
        curled += compact and (returned or folded or reach<.55)
    return curled>=3


def describe_hand(points,label,aspect=1.0):
    """points are 21 MediaPipe normalized landmarks; x/z scaled to image width."""
    p=[(v[0]*aspect,v[1],v[2]*aspect) for v in points]
    size=distance(p[5],p[17]);length=distance(p[0],p[9]);scale=max(size,length)
    center=[sum(points[i][k] for i in (0,5,9,13,17))/5 for k in (0,1)]
    fingers=True
    for mcp,pip,dip,tip in ((5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)):
        fingers &= angle(p[mcp],p[pip],p[dip])>150 and angle(p[pip],p[dip],p[tip])>145
        fingers &= distance(p[tip],p[0])>distance(p[pip],p[0])*1.12
    thumb=angle(p[2],p[3],p[4])>135 and distance(p[4],p[0])>distance(p[2],p[0])*1.08
    spread=distance(p[4],p[8])>scale*.55
    spread &= all(distance(p[a],p[b])>scale*.14 for a,b in ((8,12),(12,16),(16,20)))
    # Reject edge-on hands using projected palm area. This is not a palm/back classifier.
    u=[p[5][i]-p[0][i] for i in range(3)];v=[p[17][i]-p[0][i] for i in range(3)]
    normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    n=math.sqrt(sum(x*x for x in normal));facing=n>1e-8 and abs(normal[2])/n>.55
    orientation=math.degrees(math.atan2(p[9][0]-p[0][0],p[0][1]-p[9][1]))
    return Hand(label,center[0],center[1],max(size/aspect,length/aspect),orientation,
                bool(fingers and scale>.055),fully_closed_fist(p))

