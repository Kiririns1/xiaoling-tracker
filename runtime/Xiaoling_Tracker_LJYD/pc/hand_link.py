"""FaceTracker-step dual-axis hand follow; background network I/O."""
import json
import logging
import threading
import time
import uuid
from esp_transport import LANClient

class HandLink:
 def __init__(self,base,transport):
  self.base=base;self.transport=transport;self.lock=threading.Lock();self.state={};self.at=0
  self.config_pending=None;self.message='Connecting';self.pending=None;self.nod_pending=None;self.full_stop=False;self.generation=0;self.seq=0;self.client_id=uuid.uuid4().hex
  self.stopping=threading.Event();self.wake=threading.Event();self.thread=threading.Thread(target=self.run,daemon=True)
 def snapshot(self):
  with self.lock:return dict(self.state),self.at,self.message
 def target(self,yaw,pitch,frame_id=None,captured=0):
  with self.lock:
   if self.nod_pending is not None:return
   self.generation+=1;self.pending=(yaw,pitch,frame_id,captured,self.generation)
  self.wake.set()
 def nod(self,frame_id,captured,confirmed_frames,held_ms):
  with self.lock:
   self.generation+=1;self.pending=None
   self.nod_pending=(frame_id,captured,confirmed_frames,held_ms,self.generation)
  self.wake.set()
 def configure(self,mode,enabled):
  with self.lock:
   self.generation+=1;self.pending=None;self.nod_pending=None
   self.config_pending=(mode,enabled,time.monotonic(),self.state.get("tracking_revision"))
  self.wake.set()
 def stop_all(self):
  with self.lock:self.full_stop=True;self.pending=None;self.nod_pending=None;self.generation+=1
  self.wake.set()
 def run(self):
  client=LANClient(timeout=1.2);next_poll=0
  try:
   while not self.stopping.is_set():
    self.wake.wait(.03);self.wake.clear()
    with self.lock:
     pending=self.pending;self.pending=None;nod_pending=self.nod_pending;self.nod_pending=None
     full_stop=self.full_stop;self.full_stop=False
     config=self.config_pending;self.config_pending=None
    if config:
     mode,enabled,created,expected=config
     if time.monotonic()-created<.7 and expected is not None:
      try:
       payload={"action":"track_"+mode if enabled else "stop","expected_tracking_revision":expected}
       with self.transport.request(control=True):client.request(self.base+"/api/control",data=json.dumps(payload).encode())
      except Exception as e:
       with self.lock:self.message="Mode request outcome unknown: "+str(e)
     pending=None;nod_pending=None;next_poll=0
    if full_stop:
     try:
      state,_,_=self.snapshot()
      if state.get('mode')=='gesture_step':
       with self.transport.request(control=True):client.request(self.base+'/api/control',data=b'{"action":"stop"}')
     except Exception as e:
      with self.lock:self.message='Stop: '+str(e)
     next_poll=0;pending=None;nod_pending=None
    if nod_pending:
     frame_id,captured,frames,held_ms,generation=nod_pending;state,at,_=self.snapshot()
     if state.get('fist_nod_supported') and time.monotonic()-at<1.5:
      try:
       with self.transport.request(control=True):
        with self.lock:superseded=generation!=self.generation
        if not superseded and time.monotonic()-captured<.7:
         self.seq+=1
         payload={'frame_id':int(frame_id),'confirmed_frames':frames,'held_ms':held_ms,'client_id':self.client_id,
                  'seq':self.seq,'boot_id':state['boot_id'],'revision':state['revision']}
         code,_,body=client.request(self.base+'/api/fist-nod',data=json.dumps(payload).encode())
         with self.lock:
          self.message='Fist nod accepted' if code==202 else 'Fist nod rejected: '+body.decode('utf-8','replace')[:80]
          if code==202:self.state.update(busy=True,hand_follow_active=False,phase='waiting_fist_nod')
      except Exception as e:
       with self.lock:self.message='Fist nod outcome unknown; not retried: '+str(e)
     next_poll=0;pending=None
    if pending:
     yaw,pitch,frame_id,captured,generation=pending;moving=abs(yaw)+abs(pitch)>.001
     state,at,_=self.snapshot()
     if state.get('hand_follow_style')=='facetracker-dual-step-v1' and state.get('hand_follow_axes')=='yaw_pitch' and time.monotonic()-at<1.5:
      try:
       with self.transport.request(control=True):
        with self.lock:superseded=generation!=self.generation
        if not superseded and (not moving or time.monotonic()-captured<.7):
         self.seq+=1;payload={'yaw':yaw,'pitch':pitch,'frame_id':int(frame_id or 0),'client_id':self.client_id,
            'seq':self.seq,'boot_id':state['boot_id'],'revision':state['revision']}
         code,_,body=client.request(self.base+'/api/hand-follow',data=json.dumps(payload).encode())
         if code not in (200,409):
          with self.lock:self.message='Follow rejected: '+body.decode('utf-8','replace')[:100]
          next_poll=0
      except Exception as e:
       with self.lock:self.message='Follow network: '+str(e)
       next_poll=0
    if time.monotonic()>=next_poll:
     next_poll=time.monotonic()+.5
     try:
      with self.transport.request(control=True):code,_,body=client.request(self.base+'/api/control')
      state=json.loads(body)
      if code!=200 or state.get('mode')!='gesture_step':raise RuntimeError('Wrong Arduino interface')
      with self.lock:
       self.state=state;self.at=time.monotonic()
       self.message='' if state.get('hand_follow_style')=='facetracker-dual-step-v1' and state.get('hand_follow_axes')=='yaw_pitch' else 'Upload dual-axis follow firmware; posture still works'
     except Exception as e:
      with self.lock:self.state={};self.at=0;self.message=str(e)
  finally:
   state,_,_=self.snapshot()
   if state.get('hand_follow_supported'):
    try:
     self.seq+=1
     payload={'yaw':0,'pitch':0,'client_id':self.client_id,'seq':self.seq,'boot_id':state['boot_id'],'revision':state['revision']}
     with self.transport.request(control=True):client.request(self.base+'/api/hand-follow',data=json.dumps(payload).encode())
    except Exception:pass
   client.close()
 def close(self):self.stopping.set();self.wake.set();self.thread.join(3)
