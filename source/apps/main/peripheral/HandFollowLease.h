#pragma once
#include "MotionTypes.h"
// FaceTrackerOnly_v1/ServoControl.h state machine, with an injected PWM writer.
// Microseconds throughout. Only a NEW command can start a step; nothing queued.
class HandFollowLease {
 int64_t stopAt_=0,nextAt_=0,releaseAt_=0;
 int direction_=0;
public:
 bool active()const{return stopAt_||releaseAt_;}
 bool locked()const{return false;}
 void stop(){stopAt_=releaseAt_=0;direction_=0;}
 motion::Drive drive()const{return {stopAt_?direction_*.03f:0.f,0.f};}
 template<class Writer> bool step(int direction,int64_t now,Writer write){
  if(direction < -1 || direction > 1)return false;
  bool ok=false;
  if(direction==0){
   if(!stopAt_&&!releaseAt_)ok=true;
   else {ok=write(1500);if(ok){stopAt_=0;direction_=0;nextAt_=now+200000;if(!releaseAt_)releaseAt_=now+150000;}}
  }else if(!stopAt_&&now>=nextAt_){
   ok=write(1500-direction*75);
   if(ok){direction_=direction;releaseAt_=0;stopAt_=now+100000;}
  }
  return ok;
 }
 template<class Writer> void tick(int64_t now,Writer write){
  if(stopAt_&&now>=stopAt_){
   if(write(1500)){stopAt_=0;direction_=0;nextAt_=now+200000;releaseAt_=now+150000;}
  }
  if(!stopAt_&&releaseAt_&&now>=releaseAt_){if(write(0))releaseAt_=0;}
 }
};
