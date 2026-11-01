#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include "HandFollowLease.h"
using SemaphoreHandle_t=int;using esp_timer_handle_t=int;
struct esp_timer_create_args_t {void (*callback)(void*);const char* name;};
constexpr int pdTRUE=1,ESP_OK=0;
#define pdMS_TO_TICKS(x) (x)
static int64_t clockUs=1000000;static int originalDuty=0,newDuty=0;static bool failWrite=false;
int64_t esp_timer_get_time(){return clockUs;}
bool ledcWrite(int,uint32_t duty){if(failWrite)return false;originalDuty=duty;return true;}
bool ledcAttach(int,int,int){return true;}
int xSemaphoreCreateMutex(){return 1;}
int xSemaphoreTake(int,int){return 1;}
void xSemaphoreGive(int){}
int esp_timer_create(esp_timer_create_args_t*,int*){return 0;}
int esp_timer_start_periodic(int,int){return 0;}

// Original FaceTracker source retained here only as the comparison oracle.
// FS90R: tune neutral and offset on the actual motor.
static constexpr int SERVO_PIN=5, NEUTRAL_US=1500, OFFSET_US=75;
static SemaphoreHandle_t servoMutex;
static esp_timer_handle_t servoTimer;
static int64_t stopAt=0, nextAt=0, releaseAt=0;
static bool servoReady=false;
static bool writePulse(int us){return ledcWrite(SERVO_PIN,(uint32_t)(us*16383.0/20000.0));}
static void servoTick(void*){
 if(xSemaphoreTake(servoMutex,0)!=pdTRUE)return;
 if(stopAt && esp_timer_get_time()>=stopAt){
   if(writePulse(NEUTRAL_US)){stopAt=0;nextAt=esp_timer_get_time()+200000;releaseAt=esp_timer_get_time()+150000;}
 }
 if(!stopAt && releaseAt && esp_timer_get_time()>=releaseAt){
   if(ledcWrite(SERVO_PIN,0))releaseAt=0;
 }
 xSemaphoreGive(servoMutex);
}
static bool servoInit(){
 servoMutex=xSemaphoreCreateMutex();
 if(!servoMutex || !ledcAttach(SERVO_PIN,50,14) || !ledcWrite(SERVO_PIN,0))return false;
 esp_timer_create_args_t a={};a.callback=servoTick;a.name="tracking_stop";
 servoReady=esp_timer_create(&a,&servoTimer)==ESP_OK && esp_timer_start_periodic(servoTimer,1000)==ESP_OK;
 return servoReady;
}
static bool servoStep(int direction){
 if(!servoReady || xSemaphoreTake(servoMutex,pdMS_TO_TICKS(30))!=pdTRUE)return false;
 int64_t now=esp_timer_get_time();bool ok=false;
 if(direction==0){
   if(!stopAt && !releaseAt)ok=true;
   else {ok=writePulse(NEUTRAL_US);if(ok){stopAt=0;nextAt=now+200000;if(!releaseAt)releaseAt=now+150000;}}
 }
 else if(!stopAt && now>=nextAt){
   ok=writePulse(NEUTRAL_US-direction*OFFSET_US);
   if(ok){releaseAt=0;stopAt=esp_timer_get_time()+100000;}
 }
 xSemaphoreGive(servoMutex);return ok;
}
int main(){
 HandFollowLease actual;servoReady=true;
 auto write=[](int us){if(failWrite)return false;newDuty=us?uint32_t(us*16383.0/20000.0):0;return true;};
 auto check=[&](){assert(originalDuty==newDuty);assert(bool(stopAt||releaseAt)==actual.active());};
 auto step=[&](int d){assert(servoStep(d)==actual.step(d,clockUs,write));check();};
 auto tick=[&](){servoTick(nullptr);actual.tick(clockUs,write);check();};
 step(1);assert(newDuty==uint32_t(1425*16383.0/20000.0));
 clockUs+=99999;tick();step(-1);clockUs++;tick();assert(newDuty==uint32_t(1500*16383.0/20000.0));
 clockUs+=149999;tick();clockUs++;tick();assert(newDuty==0);
 clockUs+=49999;step(-1);clockUs++;step(-1);assert(newDuty==uint32_t(1575*16383.0/20000.0));
 step(0);clockUs+=50000;step(0);clockUs+=100000;tick();assert(newDuty==0);
 uint32_t random=12345;
 for(int i=0;i<100000;i++){
  random=random*1664525u+1013904223u;clockUs+=random%25000;
  failWrite=(random%37==0);
  if(random&1)tick();else step(int((random>>5)%3)-1);
 }
 failWrite=false;clockUs+=1000000;tick();clockUs+=150000;tick();check();
 actual.stop();assert(!actual.active()&&actual.drive().yaw==0);
 puts("PASS: original FaceTracker C++ parity, 100000 events; PWM, boundaries, cooldown rejection, stop/release, failed-write retry; cancellation.");
}
