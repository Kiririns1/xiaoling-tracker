#include "fresh_control.h"
#include "HandFollowLease.h"
#include "TimedGesture.h"
#include "driver/ledc.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <stdio.h>
#include <string.h>

static SemaphoreHandle_t gate;
static HandFollowLease follow[2];
static TimedGesture gesture;
static bool ready, fault, audio_busy, tracking, manual, settling;
static bool posture_enabled;
static unsigned posture_calibration, posture_query, posture_rotation, posture_exit;
static int selected_mode; // 0 hand, 1 face
static unsigned revision=1, boot_id, tracking_revision=1;
static int64_t pc_seen, manual_until, settle_until;
static motion::Drive manual_drive, current;
static esp_timer_handle_t timer;
static bool pulse(int axis,int us) {
 auto ch=axis?LEDC_CHANNEL_5:LEDC_CHANNEL_4;
 if(!us)return ledc_stop(LEDC_LOW_SPEED_MODE,ch,0)==ESP_OK;
 unsigned duty=(unsigned)((uint64_t)us*16383/20000);
 return ledc_set_duty(LEDC_LOW_SPEED_MODE,ch,duty)==ESP_OK&&ledc_update_duty(LEDC_LOW_SPEED_MODE,ch)==ESP_OK;
}
static bool drive(int axis,float value) {
 if(fabsf(value)<.001f)return pulse(axis,0);
 int offset=40+(int)(fabsf(value)/.35f*80);
 return pulse(axis,1500-(value>0?offset:-offset));
}
static bool following(){return follow[0].active()||follow[1].active();}
static bool busy(){return manual||settling||gesture.busy();}
static void halt() {
 follow[0].stop();follow[1].stop();gesture.stop();manual=settling=false;current={};
 bool a=pulse(0,0),b=pulse(1,0);fault=!(a&&b);++revision;
}
static void tick(void*) {
 if(!ready||xSemaphoreTake(gate,0)!=pdTRUE)return;
 int64_t now=esp_timer_get_time();
 if(tracking&&pc_seen&&now-pc_seen>3000000){tracking=false;++tracking_revision;halt();}
 if(fault){halt();xSemaphoreGive(gate);return;}
 for(int i=0;i<2;++i)follow[i].tick(now,[i](int us){bool ok=pulse(i,us);if(!ok)fault=true;return ok;});
 bool was_busy=busy();
 if(settling&&now>=settle_until){settling=false;gesture.startNod((uint32_t)(now/1000));}
 motion::Drive d;
 if(manual){if(now>=manual_until)manual=false;else d=manual_drive;}
 else if(gesture.busy())d=gesture.tick((uint32_t)(now/1000));
 if(was_busy){
  if(!drive(0,d.yaw)||!drive(1,d.pitch))fault=true;
  if(!busy())++revision;
  current=d;
 }else{current.yaw=follow[0].drive().yaw;current.pitch=follow[1].drive().yaw;}
 xSemaphoreGive(gate);
}
extern "C" bool fresh_control_init(void) {
 gate=xSemaphoreCreateMutex();if(!gate)return false;
 boot_id=esp_random();if(!boot_id)boot_id=1;
 ledc_timer_config_t t={};t.speed_mode=LEDC_LOW_SPEED_MODE;t.timer_num=LEDC_TIMER_2;t.duty_resolution=LEDC_TIMER_14_BIT;t.freq_hz=50;t.clk_cfg=LEDC_AUTO_CLK;
 if(ledc_timer_config(&t)!=ESP_OK)return false;
 for(int i=0;i<2;++i){ledc_channel_config_t c={};c.gpio_num=i?6:5;c.speed_mode=LEDC_LOW_SPEED_MODE;c.channel=i?LEDC_CHANNEL_5:LEDC_CHANNEL_4;c.timer_sel=LEDC_TIMER_2;
  if(ledc_channel_config(&c)!=ESP_OK||!pulse(i,0))return false;}
 esp_timer_create_args_t a={};a.callback=tick;a.name="tracker_guard";
 ready=esp_timer_create(&a,&timer)==ESP_OK&&esp_timer_start_periodic(timer,1000)==ESP_OK;
 return ready;
}
extern "C" unsigned tracker_boot_id(void){return boot_id;}
static bool select_checked(const char *mode,bool enable,unsigned expected) {
 if(!ready||!mode||(strcmp(mode,"hand")&&strcmp(mode,"face")))return false;
 xSemaphoreTake(gate,portMAX_DELAY);if(expected&&expected!=tracking_revision){xSemaphoreGive(gate);return false;}halt();if(enable)posture_enabled=false;selected_mode=!strcmp(mode,"face");tracking=enable;++tracking_revision;
 // Allow the PC to observe a voice request before enforcing its heartbeat.
 pc_seen=esp_timer_get_time();bool ok=!fault;xSemaphoreGive(gate);return ok;
}
extern "C" bool tracker_select(const char *mode,bool enable){return select_checked(mode,enable,0);}
extern "C" bool tracker_follow(float yaw,float pitch,unsigned rev) {
 if(!ready||!isfinite(yaw)||!isfinite(pitch)||fabsf(yaw)>.03001f||fabsf(pitch)>.03001f)return false;
 xSemaphoreTake(gate,portMAX_DELAY);
 bool zero=fabsf(yaw)+fabsf(pitch)<.001f;
 bool ok=rev==revision&&(zero||(tracking&&!audio_busy&&!fault&&!busy()));
 if(ok){bool accepted[2];float values[]={yaw,pitch};int64_t now=esp_timer_get_time();
  for(int i=0;i<2;++i){int dir=fabsf(values[i])<.001f?0:values[i]>0?1:-1;accepted[i]=follow[i].step(dir,now,[i](int us){bool result=pulse(i,us);if(!result)fault=true;return result;});}
  ok=(accepted[0]||accepted[1])&&!fault;}
 xSemaphoreGive(gate);return ok;
}
extern "C" bool fresh_control_try_gesture(bool nod,unsigned expected) {
 if(!ready){return false;}
 xSemaphoreTake(gate,portMAX_DELAY);
 bool ok=revision==expected&&!fault&&!busy();
 if(ok){halt();ok=!fault;if(ok){if(nod){settling=true;settle_until=esp_timer_get_time()+200000;}else gesture.start((uint32_t)(esp_timer_get_time()/1000));}}
 xSemaphoreGive(gate);return ok;
}
extern "C" bool tracker_fist_nod(unsigned rev){
 if(!ready){return false;}
 xSemaphoreTake(gate,portMAX_DELAY);bool allowed=tracking&&!audio_busy&&selected_mode==0;xSemaphoreGive(gate);
 return allowed&&fresh_control_try_gesture(true,rev);
}
extern "C" bool fresh_control_try_shake(unsigned rev){return fresh_control_try_gesture(false,rev);}
extern "C" bool tracker_posture_action(const char *a) {
 if(!ready||!a)return false;
 xSemaphoreTake(gate,portMAX_DELAY);bool ok=true;
 if(!strcmp(a,"posture_on")){halt();posture_enabled=true;selected_mode=1;tracking=true;++tracking_revision;pc_seen=esp_timer_get_time();}
 else if(!strcmp(a,"posture_off")){halt();posture_enabled=false;tracking=false;++tracking_revision;}
 else if(!strcmp(a,"posture_calibrate")){if(posture_enabled){halt();++posture_calibration;}else ok=false;}
 else if(!strcmp(a,"posture_pause")){if(posture_enabled){halt();tracking=false;++tracking_revision;}else ok=false;}
 else if(!strcmp(a,"posture_resume")){if(posture_enabled){halt();tracking=true;++tracking_revision;pc_seen=esp_timer_get_time();}else ok=false;}
 else if(!strcmp(a,"posture_status")){++posture_query;}
 else if(!strcmp(a,"posture_exit")){halt();tracking=false;posture_enabled=false;++tracking_revision;++posture_exit;}
 else if(!strcmp(a,"posture_rotate")){halt();++posture_rotation;}
 else ok=false;
 ok=ok&&!fault;xSemaphoreGive(gate);return ok;
}
extern "C" bool fresh_control_action(const char *a,float speed,int ms) {
 if(!a||!ready)return false;
 if(!strncmp(a,"posture_",8))return tracker_posture_action(a);
 if(!strcmp(a,"track_hand"))return tracker_select("hand",true);
 if(!strcmp(a,"track_face"))return tracker_select("face",true);
 if(!strcmp(a,"track_on"))return tracker_select(selected_mode?"face":"hand",true);
 if(!strcmp(a,"nod")||!strcmp(a,"shake"))return fresh_control_try_gesture(!strcmp(a,"nod"),fresh_control_revision());
 if(!strcmp(a,"stop")){xSemaphoreTake(gate,portMAX_DELAY);tracking=false;++tracking_revision;halt();bool ok=!fault;xSemaphoreGive(gate);return ok;}
 if(ms<20||ms>500||!isfinite(speed)||speed<=0||speed>.35f)return false;
 motion::Drive d;
 if(!strcmp(a,"left"))d.yaw=-.07f;else if(!strcmp(a,"right"))d.yaw=.07f;else if(!strcmp(a,"up"))d.pitch=.07f;else if(!strcmp(a,"down"))d.pitch=-.07f;else return false;
 xSemaphoreTake(gate,portMAX_DELAY);bool ok=!busy()&&!fault;
 if(ok){halt();manual=true;manual_drive=d;manual_until=esp_timer_get_time()+(int64_t)ms*1000;}
 xSemaphoreGive(gate);return ok;
}
extern "C" void fresh_control_audio(bool value){
 if(!ready){return;}
 xSemaphoreTake(gate,portMAX_DELAY);audio_busy=value;
 if(value&&following()){follow[0].stop();follow[1].stop();pulse(0,0);pulse(1,0);current={};}
 xSemaphoreGive(gate);
}
extern "C" unsigned fresh_control_revision(void){if(!gate)return 0;xSemaphoreTake(gate,portMAX_DELAY);unsigned r=revision;xSemaphoreGive(gate);return r;}
extern "C" void fresh_control_shake(bool start){if(start)fresh_control_try_shake(fresh_control_revision());}
extern "C" bool fresh_control_plan(const fresh_step_t*,int,int,int){return false;}
extern "C" bool fresh_control_plan_axes(const fresh_step_t*,const int*,int,int,int){return false;}
extern "C" bool fresh_control_step(float speed,unsigned rev){return tracker_follow(speed,0,rev);}
extern "C" const char *fresh_control_step_error(float speed,unsigned rev){return fresh_control_step(speed,rev)?nullptr:"follow_rejected";}
extern "C" bool fresh_control_json(const cJSON *j){
 const cJSON *a=cJSON_GetObjectItemCaseSensitive(j,"action"),*v=cJSON_GetObjectItemCaseSensitive(j,"duration_ms");
 if(!cJSON_IsString(a)){return false;}
 int ms=300;
 const cJSON *expected=cJSON_GetObjectItem(j,"expected_tracking_revision");
 if(expected){
  if(!cJSON_IsNumber(expected)||!isfinite(expected->valuedouble)||expected->valuedouble<1||expected->valuedouble>4294967295.0||floor(expected->valuedouble)!=expected->valuedouble)return false;
  bool stop=!strcmp(a->valuestring,"stop");const char *mode=!strcmp(a->valuestring,"track_hand")?"hand":!strcmp(a->valuestring,"track_face")?"face":(stop||!strcmp(a->valuestring,"track_on"))?(selected_mode?"face":"hand"):nullptr;
  return mode&&select_checked(mode,!stop,(unsigned)expected->valuedouble);
 }
 if(v){if(!cJSON_IsNumber(v)||!isfinite(v->valuedouble)||floor(v->valuedouble)!=v->valuedouble)return false;ms=v->valueint;}
 return fresh_control_action(a->valuestring,.07f,ms);
}
extern "C" void fresh_control_state(char *out,unsigned cap,bool heartbeat) {
 if(!ready){snprintf(out,cap,"{\"ready\":false}");return;}
 xSemaphoreTake(gate,portMAX_DELAY);if(heartbeat)pc_seen=esp_timer_get_time();
 snprintf(out,cap,"{\"ready\":%s,\"mode\":\"gesture_step\",\"revision\":%u,\"boot_id\":%u,\"tracking_enabled\":%s,\"tracking_mode\":\"%s\",\"tracking_revision\":%u,\"busy\":%s,\"fault\":%s,\"phase\":\"%s\",\"audio_busy\":%s,\"hand_follow_style\":\"facetracker-dual-step-v1\",\"hand_follow_axes\":\"yaw_pitch\",\"hand_follow_supported\":true,\"face_follow_supported\":true,\"face_follow_axes\":\"yaw_pitch\",\"fist_nod_supported\":true,\"hand_follow_active\":%s,\"hand_follow_locked\":false,\"fist_nod_speed\":0.025,\"fist_nod_stroke_ms\":300,\"fist_nod_pause_ms\":200,\"follow_pulse_us\":75,\"follow_step_ms\":100,\"follow_pause_ms\":200,\"yaw_speed\":%.3f,\"pitch_speed\":%.3f,\"yaw_gpio\":5,\"pitch_gpio\":6,\"feedback_mode\":\"timed\",\"return_verified\":false,\"posture_enabled\":%s,\"posture_calibration\":%u,\"posture_query\":%u,\"posture_rotation\":%u,\"posture_exit\":%u}",fault?"false":"true",revision,boot_id,tracking?"true":"false",selected_mode?"face":"hand",tracking_revision,(busy()||following())?"true":"false",fault?"true":"false",settling?"waiting_fist_nod":gesture.busy()?"gesture":manual?"manual":following()?"hand_follow":"idle",audio_busy?"true":"false",following()?"true":"false",current.yaw,current.pitch,posture_enabled?"true":"false",posture_calibration,posture_query,posture_rotation,posture_exit);
 xSemaphoreGive(gate);
}
