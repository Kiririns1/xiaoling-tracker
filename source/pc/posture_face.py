"""Use the same pose person's facial landmarks for two-axis camera following."""
import math
from face_follow import Face, FaceFollower
from posture_config import FACE_TARGET_Y

def pose_face(points,width,height):
    if width<=0 or height<=0:return None
    face=[points[i] for i in (0,2,5)]
    if any(p is None for p in face):return None
    if not all(math.isfinite(v) for p in face for v in p):return None
    x=sum(p[0] for p in face)/3/width
    y=sum(p[1] for p in face)/3/height
    if not (0<=x<=1 and 0<=y<=1):return None
    eye_width=abs(face[1][0]-face[2][0])/width
    if eye_width<.015:return None
    return Face(x,y,max(.06,eye_width*2))

class PostureFaceFollower(FaceFollower):
    def update(self,faces,now):
        # Aim above image center to keep both shoulders in view.
        shifted=[Face(f.x,f.y+.5-FACE_TARGET_Y,f.size) for f in faces]
        return super().update(shifted,now)
