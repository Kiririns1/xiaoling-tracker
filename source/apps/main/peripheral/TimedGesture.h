#pragma once
#include "MotionTypes.h"
#include "GestureConfig.h"
// Timed gesture. Completion only means
// pulses ended, never that the camera's position was measured or restored.
class TimedGesture {
 bool active_=false,finished_=false,nod_=false;uint32_t started_=0;
public:
 bool busy()const{return active_;}bool done()const{return finished_;}
 void stop(){active_=finished_=false;}
 bool nodding()const{return active_&&nod_;}
 void startNod(uint32_t now){start(now);nod_=true;}
 void start(uint32_t now){nod_=false;started_=now;active_=true;finished_=false;}
 motion::Drive tick(uint32_t now){
  motion::Drive d;if(!active_)return d;
  uint32_t elapsed=now-started_;
  if(nod_){
   if(elapsed<FIST_NOD_STROKE_MS)d.pitch=-FIST_NOD_SPEED;
   else if(elapsed<FIST_NOD_STROKE_MS+FIST_NOD_PAUSE_MS){}
   else if(elapsed<2*FIST_NOD_STROKE_MS+FIST_NOD_PAUSE_MS)d.pitch=FIST_NOD_SPEED;
   else {active_=false;finished_=true;}
   return d;
  }
   if(elapsed<100)d.yaw=.06f;
   else if(elapsed<200){}
   else if(elapsed<400)d.yaw=-.06f;
   else if(elapsed<500){}
   else if(elapsed<600)d.yaw=.06f;
   else {active_=false;finished_=true;}
  return d;
 }
};
