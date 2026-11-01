#include "TimedGesture.h"
#include <assert.h>
#include <stdio.h>
int main(){
 TimedGesture gesture;gesture.start(1000);int left=0,right=0;
 for(unsigned t=1000;t<2000;t+=10){auto d=gesture.tick(t);assert(d.pitch==0);if(d.yaw<0)++left;if(d.yaw>0)++right;if(t>=1600)assert(d.yaw==0&&!gesture.busy());}
 assert(left==20&&right==20&&gesture.done());
 gesture.start(0);assert(gesture.tick(10).yaw!=0);gesture.stop();assert(gesture.tick(250).yaw==0&&!gesture.done());
 gesture.start(0xfffffff0u);assert(gesture.tick(0x10u).yaw>0);assert(gesture.tick(0x300u).yaw==0&&!gesture.busy());
 gesture.startNod(1000);
 const unsigned turn=FIST_NOD_STROKE_MS,pause=FIST_NOD_PAUSE_MS;
 assert(gesture.tick(1000).yaw==0&&gesture.tick(1000).pitch==-FIST_NOD_SPEED);
 assert(gesture.tick(1000+turn-1).pitch==-FIST_NOD_SPEED);
 assert(gesture.tick(1000+turn).pitch==0&&gesture.busy());
 assert(gesture.tick(1000+turn+pause-1).pitch==0);
 assert(gesture.tick(1000+turn+pause).pitch==FIST_NOD_SPEED);
 assert(gesture.tick(1000+2*turn+pause-1).pitch==FIST_NOD_SPEED);
 assert(gesture.tick(1000+2*turn+pause).pitch==0&&!gesture.busy()&&gesture.done());
 gesture.startNod(0);gesture.stop();assert(gesture.tick(450).pitch==0);
 puts("PASS: shake and slow fist nod, timed boundaries, stop, clock wrap.");
}
