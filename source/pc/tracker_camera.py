"""Unified hand/face tracker with fist nod and posture recognition."""
import argparse
import logging
from pathlib import Path
import sys
import time
import cv2
import mediapipe as mp
import numpy as np
from esp_camera import Camera,camera_url
from esp_transport import ESPTransport,control_base
from posture_link import PostureLink
from hand_geometry import describe_hand
from hand_follow import HandFollower
from hand_link import HandLink
from fist_gate import FistGate
from light_gesture import number_gesture, NumberGate
from light_link import LightLink
from face_follow import Face,FaceFollower,TrackingModes
from detection_engines import DetectionEngines
from reacquiring_hands import ReacquiringHands
from mediapipe_detector import MediaPipeDetector
from posture import PostureFilter,metrics
from posture_config import POSE_CONFIDENCE, METRICS_LOG_SECONDS, CAMERA_SETTLE_SECONDS
from posture_face import pose_face, PostureFaceFollower

def main():
 root=Path(__file__).resolve().parents[1]
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--posture-only',action='store_true',help='Posture monitoring with automatic face following; no hand gestures');ap.add_argument('--host',default='172.20.10.2')
 ap.add_argument('--rotate',type=int,choices=(0,90,180,270),default=90)
 args=ap.parse_args();url=camera_url(args.host)
 from urllib.parse import urlsplit
 parts=urlsplit(url);base=f'{parts.scheme}://{parts.netloc}'
 (root/'validation').mkdir(parents=True,exist_ok=True)
 logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',handlers=[logging.StreamHandler(sys.stdout),logging.FileHandler(root/'validation/gesture_live.log',mode='w',encoding='utf-8')],force=True)
 log=logging.getLogger('hand');transport=ESPTransport(split=True)
 camera=Camera(url,fps=10,quality=55,transport=transport);link=HandLink(control_base(base),transport)
 follower=HandFollower();face_follower=FaceFollower();modes=TrackingModes();policy=PostureFilter();fist=FistGate();nod_until=-100.
 posture_follower=PostureFaceFollower();posture_follow_enabled=True
 light_gate=NumberGate();light_link=LightLink(control_base(base),transport)
 # Video landmarks stay continuous; recovery searches the full frame and last hand region.
 detectors=DetectionEngines(
  lambda:ReacquiringHands(
   lambda:mp.solutions.hands.Hands(static_image_mode=False,max_num_hands=2,model_complexity=1,min_detection_confidence=.35,min_tracking_confidence=.35),
   lambda:mp.solutions.hands.Hands(static_image_mode=True,max_num_hands=2,model_complexity=1,min_detection_confidence=.10,min_tracking_confidence=.5)),
  lambda:mp.solutions.face_detection.FaceDetection(model_selection=0,min_detection_confidence=.55))
 pose=None
 follow_enabled=False;posture_enabled=False;seen=-1;annotated=None;state={};last_boot=None
 last_command=(0.,0.);last_motion=-100.;was_moving=False;posture_text='坐姿检测已关闭，P开启';posture_ui='Posture OFF (P enables)'
 last_posture_log=0;last_log=0;hand_count=0;message='Connecting'
 window='Xiaoling Tracker | 1 HAND 2 FACE M switch | SPACE stop'
 posture_link=PostureLink(control_base(base),transport);posture_link.thread.start()
 calibration_deadline=0.;last_tracking_revision=None;last_calibration=0;last_query=0;last_rotation=0;last_exit=0;remote_key=None;initial_posture=args.posture_only
 camera.thread.start();link.thread.start();light_link.thread.start()
 if posture_enabled:link.stop_all()
 log.info('手/脸检测器互斥，手模式连续视频跟踪，漏检时全图及局部恢复。坐姿默认关闭，P开启。')
 log.info('1手部双轴追踪，2人脸双轴追踪，M切换模式。握拳判断已放宽，仍需6帧且0.6秒；张手后重新准备。F追踪开关；P坐姿开关；C坐姿校准；空格停止；R旋转；Q退出。')
 try:
  while True:
   now=time.monotonic();state,state_at,message=link.snapshot()
   if state and state.get('boot_id')!=last_boot:
    last_exit=state.get('posture_exit',0);last_calibration=state.get('posture_calibration',0);last_query=state.get('posture_query',0);last_rotation=state.get('posture_rotation',0);last_tracking_revision=None;last_boot=state.get('boot_id');detectors.reset();follower.reset();face_follower.reset();posture_follower.reset();fist.pause();light_gate.reset();policy.reset();last_command=(0.,0.)
   remote_key=None
   if state and now-state_at<1.5:
    if initial_posture:
     posture_link.action('posture_on',state);initial_posture=False
    if state.get('posture_exit',0)!=last_exit:break
    enabled=bool(state.get('posture_enabled',False))
    changed=enabled!=posture_enabled
    if changed:
     posture_enabled=enabled;calibration_deadline=0.;policy.reset();posture_follower.reset();detectors.close();follower.reset();face_follower.reset();fist.pause();light_gate.reset()
     last_command=(0.,0.);nod_until=-100.;last_motion=now;annotated=None;seen=-1
     if not enabled and pose is not None:pose.close();pose=None
     posture_link.report('enabled' if enabled else 'disabled',state)
    remote_revision=state.get('tracking_revision')
    if remote_revision!=last_tracking_revision or follow_enabled!=bool(state.get('tracking_enabled',False)):
     last_tracking_revision=remote_revision;follow_enabled=bool(state.get('tracking_enabled',False));posture_follow_enabled=follow_enabled
     modes.mode=state.get('tracking_mode','hand')
     if modes.mode not in ('hand','face'):modes.mode='hand'
     if not posture_enabled:detectors.select(modes.mode);policy.reset()
     follower.reset();face_follower.reset();posture_follower.reset();fist.pause();light_gate.reset()
     last_command=(0.,0.);nod_until=-100.;seen=-1
    calibration=state.get('posture_calibration',0)
    if calibration!=last_calibration:
     last_calibration=calibration;calibration_deadline=now+5.;link.target(0,0);last_command=(0.,0.);last_motion=now
    rotation=state.get('posture_rotation',0)
    if rotation!=last_rotation:
     delta=(rotation-last_rotation)%4;last_rotation=rotation;args.rotate=(args.rotate+90*delta)%360
     policy.reset();posture_follower.reset();detectors.reset();annotated=None;seen=-1
    query=state.get('posture_query',0)
    if query!=last_query:
     last_query=query;posture_link.report('disabled' if not posture_enabled else 'calibrating' if policy.calibrating else 'uncalibrated' if policy.baseline is None else 'monitoring',state)
   with camera.lock:
    raw=None if camera.frame is None else camera.frame.copy();number=camera.number
    frame_id=camera.image_frame_id;captured=camera.captured_at
   fresh=raw is not None and time.monotonic()-captured<.70
   can_follow=bool(state.get('tracking_enabled',False) and state.get('hand_follow_style')=='facetracker-dual-step-v1' and state.get('hand_follow_axes')=='yaw_pitch' and not state.get('fault') and not state.get('audio_busy') and
       (not state.get('busy') or state.get('hand_follow_active')) and now-state_at<1.5)
   if fresh and number!=seen:
    seen=number;frame=raw
    if args.rotate:frame=cv2.rotate(frame,{90:cv2.ROTATE_90_CLOCKWISE,180:cv2.ROTATE_180,270:cv2.ROTATE_90_COUNTERCLOCKWISE}[args.rotate])
    frame=cv2.flip(frame,1);rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB);rgb.flags.writeable=False
    observations=[]
    if posture_enabled:
     if pose is None:pose=MediaPipeDetector(POSE_CONFIDENCE,'lite')
     frame=pose.process(frame)
    if posture_enabled:
     detected_face=pose_face(pose.points,frame.shape[1],frame.shape[0])
     if detected_face is not None:observations.append(detected_face)
     active_follower=posture_follower
    elif args.posture_only:
     active_follower=follower
    elif modes.mode=='hand':
     result=detectors.process('hand',rgb,time.monotonic())
     if detectors.restarted:
      follower.reset();fist.pause();light_gate.reset();log.info('No hand detected: automatic full-frame re-detection #%d',detectors.recoveries)
     for i,landmarks in enumerate(result.multi_hand_landmarks or []):
      classifications=result.multi_handedness or [];label=classifications[i].classification[0].label if i<len(classifications) else f'Hand{i+1}'
      hand=describe_hand([(p.x,p.y,p.z) for p in landmarks.landmark],label,frame.shape[1]/frame.shape[0]);hand.light_number=number_gesture([(p.x,p.y,p.z) for p in landmarks.landmark],frame.shape[1]/frame.shape[0]);observations.append(hand)
      drawing=result.display_hand_landmarks[i]
      mp.solutions.drawing_utils.draw_landmarks(frame,drawing,mp.solutions.hands.HAND_CONNECTIONS)
      cv2.putText(frame,label,(round(hand.x*frame.shape[1]),round(hand.y*frame.shape[0])),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,255,255),1)
     for held in result.held_hand_landmarks:
      gray=mp.solutions.drawing_utils.DrawingSpec(color=(150,150,150),thickness=1,circle_radius=1)
      mp.solutions.drawing_utils.draw_landmarks(frame,held,mp.solutions.hands.HAND_CONNECTIONS,gray,gray)
     active_follower=follower
    else:
     result=detectors.process('face',rgb,time.monotonic())
     for detection in result.detections or []:
      box=detection.location_data.relative_bounding_box
      x=box.xmin+box.width/2;y=box.ymin+box.height/2
      if not (0<=x<=1 and 0<=y<=1):continue
      observations.append(Face(x,y,max(box.width,box.height)))
      h,w=frame.shape[:2]
      cv2.rectangle(frame,(max(0,int(box.xmin*w)),max(0,int(box.ymin*h))),(min(w-1,int((box.xmin+box.width)*w)),min(h-1,int((box.ymin+box.height)*h))),(0,255,255),1)
     active_follower=face_follower
    hand_count=len(observations)
    command=active_follower.update(observations,time.monotonic()) if ((posture_enabled and posture_follow_enabled and not policy.calibrating and not calibration_deadline) or (not posture_enabled and not args.posture_only and follow_enabled)) and can_follow and now>=nod_until else (0.,0.)
    eligible=not posture_enabled and modes.mode=='hand' and follow_enabled and can_follow and now>=nod_until and state.get('fist_nod_supported',False)
    selected=follower.selected if eligible else None
    if eligible:
     request_nod=fist.update(selected,follower.track_id,frame_id,captured,time.monotonic())
    else:fist.pause();light_gate.reset();request_nod=False
    percent=light_gate.update(getattr(selected,'light_number',None),follower.track_id,frame_id,captured,time.monotonic())
    if percent is not None:light_link.send('brightness',state.get('boot_id'),percent)
    if request_nod:
     light_link.send('toggle',state.get('boot_id'))
     link.nod(frame_id,captured,*fist.confirmation);nod_until=now+2.;command=(0.,0.)
     log.info('Closed fist confirmed across %d frames: one slow nod',fist.confirmation[0])
    else:
     if selected is not None and getattr(selected,'fist',False) and fist.armed:command=(0.,0.)
     if command!=(0.,0.) or last_command!=(0.,0.):link.target(*command,frame_id,captured)
    last_command=command
    moving=request_nod or now<nod_until or command!=(0.,0.) or state.get('hand_follow_active',False) or state.get('busy',False)
    if moving:
     if not was_moving and not posture_enabled:policy.reset()
     was_moving=True;last_motion=now;policy.invalidate();posture_text='摄像头运动中，暂停坐姿判断';posture_ui='Posture paused: camera moving'
    elif now-last_motion<CAMERA_SETTLE_SECONDS:
     policy.invalidate();posture_ui='Waiting for camera to settle'
    elif posture_enabled:
     was_calibrating=policy.calibrating
     was_moving=False;posture_text,_,alert=policy.observe(metrics(pose.points,require_eyes=True),time.monotonic())
     if was_calibrating and not policy.calibrating and policy.baseline is not None:posture_link.report('calibrated',state)
     if policy.calibrating:posture_ui='Calibrating: sit still'
     elif policy.baseline is None:posture_ui='Sit straight and press C'
     elif '无法判断' in posture_text:posture_ui='Pose missing: nose + eyes + shoulders needed'
     elif '阈值范围' in posture_text:posture_ui='Posture OK'
     elif '前倾' in posture_text:posture_ui='Warning: leaning forward'
     elif '向画面左' in posture_text:posture_ui='Warning: leaning LEFT (screen)'
     elif '向画面右' in posture_text:posture_ui='Warning: leaning RIGHT (screen)'
     else:posture_ui='Adjust posture (details in terminal)'
     if alert:
      log.warning('[坐姿提醒] %s',posture_text)
      if state.get('boot_id') is not None and now-state_at<1.5:posture_link.report('alert',state)
     if now-last_posture_log>=METRICS_LOG_SECONDS:
      last_posture_log=now;pm=metrics(pose.points,require_eyes=True);pb=policy.baseline
      if pm is not None and pb is not None:
       log.info('[坐姿参数] 肩角差=%+.1f度 鼻肩缩短=%.1f%% 眼肩缩短=%.1f%% 肩宽倍数=%.2f | %s',pm[0]-pb[0],100*(1-pm[2]/pb[2]),100*(1-pm[4]/pb[4]),pm[3]/pb[3],posture_text)
    else:posture_ui='Posture OFF (P enables)'
    # Both axes use the same center zone and independent step timing.
    h,w=frame.shape[:2];cv2.rectangle(frame,(int(w*.36),int(h*.36)),(int(w*.64),int(h*.64)),(255,180,0),1)
    annotated=frame.copy()
   elif not fresh:
    policy.invalidate();follower.reset();face_follower.reset();posture_follower.reset();fist.pause()
    if last_command!=(0.,0.):link.target(0,0);last_command=(0.,0.)
    posture_ui='Posture paused: stale image'
   if not can_follow and last_command!=(0.,0.):link.target(0,0);last_command=(0.,0.)
   display=annotated.copy() if annotated is not None else np.zeros((240,320,3),np.uint8)
   display=cv2.copyMakeBorder(display,96,0,0,0,cv2.BORDER_CONSTANT,value=(25,25,25))
   mode=('HAND: DUAL AXIS' if modes.mode=='hand' else 'FACE: DUAL AXIS')+(' ON' if follow_enabled else ' OFF')
   if posture_enabled:mode='POSTURE + FACE FOLLOW '+('ON' if posture_follow_enabled else 'PAUSED')
   if not fresh:mode+=' | STALE IMAGE'
   for i,text in enumerate((mode+f' | targets {hand_count}',posture_ui,
        posture_follower.message if posture_enabled else (((fist.message or follower.message) if modes.mode=='hand' else face_follower.message) if can_follow and follow_enabled else message or 'F enables/disables tracking'),
        ('POSTURE: C calibrate F follow SPACE stop P exit Q quit' if posture_enabled or args.posture_only else '1 hand 2 face M switch F control P posture C calibrate'))):
    cv2.putText(display,text[:90],(6,17+23*i),cv2.FONT_HERSHEY_SIMPLEX,.35,(0,220,255),1)
   cv2.imshow(window,display)
   if now-last_log>=2:log.info('[追踪] mode=%s targets=%s follow=%s supported=%s fresh=%s | %s | posture=%s',modes.mode,hand_count,follow_enabled,state.get('hand_follow_supported',False),fresh,follower.message if modes.mode=='hand' else face_follower.message,posture_text);last_log=now
   key=cv2.waitKey(10)&255
   if remote_key is not None:key=remote_key
   if key in (ord('q'),27):break
   if key in (ord('f'),32):
    if posture_enabled:posture_link.action('posture_pause' if key==32 or posture_follow_enabled else 'posture_resume',state)
    else:link.configure(modes.mode,not follow_enabled if key==ord('f') else False)
   if key==ord('p'):posture_link.action('posture_off' if posture_enabled else 'posture_on',state)
   if key==ord('c'):
    calibration_deadline=now+5.;link.target(0,0);last_command=(0.,0.);last_motion=now
   if calibration_deadline:
    if posture_enabled and fresh and time.monotonic()-last_motion>CAMERA_SETTLE_SECONDS and not state.get('busy') and not state.get('audio_busy') and not state.get('hand_follow_active') and pose is not None and metrics(pose.points,require_eyes=True) is not None:
     policy.start_calibration(time.monotonic());calibration_deadline=0.;posture_link.report('calibrating',state)
    elif now>=calibration_deadline or not posture_enabled:
     calibration_deadline=0.;posture_link.report('calibration_rejected',state)
   if not posture_enabled and not args.posture_only and modes.select(key):
    link.configure(modes.mode,follow_enabled);last_command=(0.,0.);nod_until=-100.
    detectors.select(modes.mode);follower.reset();face_follower.reset();posture_follower.reset();fist.pause();light_gate.reset();policy.reset()
    last_motion=now;was_moving=True;annotated=None;seen=-1
    log.info('Tracking mode: %s; old target and queued actions cleared',modes.mode)
   if key==ord('r'):
    link.target(0,0);last_command=(0.,0.);args.rotate=(args.rotate+90)%360
    detectors.reset();policy.reset();follower.reset();face_follower.reset();posture_follower.reset();fist.pause();light_gate.reset();annotated=None;seen=-1
 finally:
  camera.stop.set();camera.thread.join(3);posture_link.close();link.close();light_link.close();detectors.close()
  if pose is not None:pose.close()
  cv2.destroyAllWindows()

if __name__=='__main__':main()
