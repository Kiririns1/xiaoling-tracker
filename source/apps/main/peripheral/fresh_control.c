#include "fresh_control.h"
#include "fresh_hardware.h"
#include "driver/ledc.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

static SemaphoreHandle_t gate;
static bool ready, audio_busy, pending, gesture, resume_tracking;
static int mode, count, index_step, cycles, interval_ms;
static unsigned revision=1;
static int64_t pc_seen, deadline, queued_at;
static bool gap;
static float speed_now;
static float pitch_speed;
static int gesture_axis;
static fresh_step_t plan[32];
static int plan_axes[32];
static esp_timer_handle_t clock_timer;

static bool drive_axis(float speed,int axis) {
    ledc_channel_t channel=axis?LEDC_CHANNEL_5:LEDC_CHANNEL_4;
    esp_err_t ret;
    if (speed==0) ret=ledc_stop(LEDC_LOW_SPEED_MODE,channel,0);
    else {
        float offset=65+fabsf(speed)/.35f*85;
        if(axis)offset*=speed>0?FRESH_PITCH_UP_GAIN:FRESH_PITCH_DOWN_GAIN;
        float direction=axis?FRESH_PITCH_UP_SIGN:1;
        unsigned duty=(unsigned)(((axis?FRESH_PITCH_NEUTRAL_US:1500)-direction*(speed>0?offset:-offset))*16383/20000);
        ret=ledc_set_duty(LEDC_LOW_SPEED_MODE,channel,duty);
        if(ret==ESP_OK) ret=ledc_update_duty(LEDC_LOW_SPEED_MODE,channel);
    }
    if(ret==ESP_OK){if(axis)pitch_speed=speed;else speed_now=speed;}
    return ret==ESP_OK;
}
static bool drive(float speed){return drive_axis(speed,gesture_axis);}
static void halt(void) { drive_axis(0,0);drive_axis(0,1);gesture_axis=0;mode=0;pending=false;gesture=false;deadline=0;++revision; }
static void start_step(int64_t now) {
    gesture_axis=plan_axes[index_step];
    if(!drive(plan[index_step].speed)) {halt();return;}
    deadline=now+(int64_t)plan[index_step].duration_ms*1000;
}
static void tick(void *unused) {
    (void)unused;
    if(!ready||xSemaphoreTake(gate,0)!=pdTRUE)return;
    int64_t now=esp_timer_get_time();
    if(mode==1) {
        if(now-pc_seen>3000000) halt();
        else if(audio_busy||(deadline&&now>=deadline)) { drive(0);deadline=0; }
    } else if(mode==2) {
        if(pending) {
            if(now-queued_at>30000000)halt();
            else if(!audio_busy){pending=false;start_step(now);}
        } else if(audio_busy&&!gesture) halt();
        else if(now>=deadline) {
            if(gap){gap=false;start_step(now);}
            else {
                drive(0);++index_step;
                if(index_step==count){index_step=0;--cycles;
                    if(!cycles){bool resume=gesture&&resume_tracking&&now-pc_seen<3000000;halt();if(resume)mode=1;}
                    else if(interval_ms){gap=true;deadline=now+(int64_t)interval_ms*1000;}
                }
                if(mode==2&&!gap)start_step(now);
            }
        }
    }
    xSemaphoreGive(gate);
}
bool fresh_control_init(void) {
    gate=xSemaphoreCreateMutex();if(!gate)return false;
    ledc_timer_config_t t={.speed_mode=LEDC_LOW_SPEED_MODE,.timer_num=LEDC_TIMER_2,.duty_resolution=LEDC_TIMER_14_BIT,.freq_hz=50,.clk_cfg=LEDC_AUTO_CLK};
    ledc_channel_config_t c={.gpio_num=FRESH_YAW_GPIO,.speed_mode=LEDC_LOW_SPEED_MODE,.channel=LEDC_CHANNEL_4,.timer_sel=LEDC_TIMER_2,.duty=0};
    if(ledc_timer_config(&t)!=ESP_OK||ledc_channel_config(&c)!=ESP_OK||!drive(0))return false;
    c.gpio_num=FRESH_PITCH_GPIO;c.channel=LEDC_CHANNEL_5;
    if(ledc_channel_config(&c)!=ESP_OK||!drive_axis(0,1))return false;
    esp_timer_create_args_t a={.callback=tick,.name="fresh_motion"};
    ready=esp_timer_create(&a,&clock_timer)==ESP_OK&&esp_timer_start_periodic(clock_timer,20000)==ESP_OK;
    return ready;
}
bool fresh_control_plan(const fresh_step_t *steps,int n,int repeat,int interval) {
    return fresh_control_plan_axes(steps,NULL,n,repeat,interval);
}
bool fresh_control_plan_axes(const fresh_step_t *steps,const int *axes,int n,int repeat,int interval) {
    if(!ready||!steps||n<1||n>32||repeat<1||repeat>100||interval<0||interval>3600000)return false;
    int64_t total=0;
    int64_t pitch_total=0;
    for(int i=0;i<n;++i){if(!isfinite(steps[i].speed)||fabsf(steps[i].speed)>.35f||steps[i].duration_ms<1||steps[i].duration_ms>3600000)return false;total+=steps[i].duration_ms;}
    for(int i=0;i<n;++i){int axis=axes?axes[i]:0;if(axis<0||axis>1)return false;if(axis&&steps[i].speed!=0){if(steps[i].duration_ms>FRESH_PITCH_STEP_MAX_MS)return false;pitch_total+=steps[i].duration_ms;}}
    if(pitch_total*repeat>FRESH_PITCH_PLAN_MAX_MS)return false;
    if(total*repeat+(int64_t)interval*(repeat-1)>3600000)return false;
    xSemaphoreTake(gate,portMAX_DELAY);halt();memcpy(plan,steps,n*sizeof(*steps));count=n;index_step=0;cycles=repeat;interval_ms=interval;gap=false;mode=2;
    for(int i=0;i<n;++i)plan_axes[i]=axes?axes[i]:0;
    queued_at=esp_timer_get_time();pending=audio_busy;if(!pending)start_step(queued_at);
    xSemaphoreGive(gate);return true;
}
bool fresh_control_action(const char *action,float speed,int ms) {
    if(!ready||!action)return false;
    if(!strcmp(action,"stop")||!strcmp(action,"track_on")) {
        xSemaphoreTake(gate,portMAX_DELAY);bool ok=strcmp(action,"track_on")|| (pc_seen&&esp_timer_get_time()-pc_seen<3000000);
        if(ok){halt();if(!strcmp(action,"track_on"))mode=1;}xSemaphoreGive(gate);return ok;
    }
    bool pitch=!strcmp(action,"up")||!strcmp(action,"down");
    if(!isfinite(speed)||speed<=0||speed>.35f|| (!pitch&&strcmp(action,"left")&&strcmp(action,"right")))return false;
    fresh_step_t step={(!strcmp(action,"right")||!strcmp(action,"up"))?speed:-speed,ms};int axis=pitch?1:0;return fresh_control_plan_axes(&step,&axis,1,1,0);
}
bool fresh_control_step(float speed,unsigned rev) {
    return fresh_control_step_error(speed,rev)==NULL;
}
const char *fresh_control_step_error(float speed,unsigned rev){
    if(!ready)return "not_ready";
    if(!isfinite(speed)||fabsf(speed)>.35f)return "invalid_speed";
    xSemaphoreTake(gate,portMAX_DELAY);const char *error=NULL;
    if(revision!=rev)error="stale_revision";
    else if(mode!=1)error="not_tracking";
    else if(audio_busy&&speed!=0)error="audio_busy";
    else if(!drive_axis(speed,0))error="pwm_failed";
    else deadline=esp_timer_get_time()+350000;
    xSemaphoreGive(gate);return error;
}
void fresh_control_audio(bool busy) {if(!ready)return;xSemaphoreTake(gate,portMAX_DELAY);audio_busy=busy;if(busy&&!gesture){drive(0);if(mode==2&&!pending)halt();}xSemaphoreGive(gate);}
void fresh_control_shake(bool start) {
    if(!ready){return;}
    xSemaphoreTake(gate,portMAX_DELAY);
    if(start) {
        resume_tracking=mode==1;halt();
        fresh_step_t s[]={{.12f,150},{0,100},{-.12f,300},{0,100},{.12f,150}};
        for(int i=0;i<5;++i)plan_axes[i]=0;
        memcpy(plan,s,sizeof(s));count=5;index_step=0;cycles=1;interval_ms=0;gap=false;mode=2;gesture=true;start_step(esp_timer_get_time());
    }else if(gesture){bool resume=resume_tracking&&esp_timer_get_time()-pc_seen<3000000;halt();if(resume)mode=1;}
    xSemaphoreGive(gate);
}
unsigned fresh_control_revision(void){if(!ready)return 0;xSemaphoreTake(gate,portMAX_DELAY);unsigned r=revision;xSemaphoreGive(gate);return r;}
bool fresh_control_try_shake(unsigned expected){
 return fresh_control_try_gesture(false,expected);
}
bool fresh_control_try_gesture(bool nod,unsigned expected){
 if(!ready){return false;}
 xSemaphoreTake(gate,portMAX_DELAY);
 bool ok=revision==expected&&mode!=2;
 if(ok){resume_tracking=mode==1;halt();
  if(nod){fresh_step_t s[]={{FRESH_NOD_SPEED,FRESH_NOD_OUT_MS},{0,FRESH_NOD_PAUSE_MS},{-FRESH_NOD_SPEED,FRESH_NOD_BACK_MS}};memcpy(plan,s,sizeof(s));count=3;gesture_axis=1;}
  else{fresh_step_t s[]={{.12f,150},{0,100},{-.12f,300},{0,100},{.12f,150}};memcpy(plan,s,sizeof(s));count=5;}
  for(int i=0;i<count;++i)plan_axes[i]=nod?1:0;
  index_step=0;cycles=1;interval_ms=0;gap=false;mode=2;gesture=true;start_step(esp_timer_get_time());}
 xSemaphoreGive(gate);return ok;
}
void fresh_control_state(char *out,unsigned cap,bool heartbeat) {
    if(!ready){snprintf(out,cap,"{\"ready\":false}");return;}
    xSemaphoreTake(gate,portMAX_DELAY);int64_t now=esp_timer_get_time();if(heartbeat)pc_seen=now;
    snprintf(out,cap,"{\"ready\":true,\"mode\":\"%s\",\"revision\":%u,\"speed\":%.3f,\"pitch_speed\":%.3f,\"yaw_gpio\":%d,\"pitch_gpio\":%d,\"pc_online\":%s,\"audio_busy\":%s,\"step\":%d,\"remaining_cycles\":%d}",mode==1?"tracking":mode==2?"manual":"off",revision,speed_now,pitch_speed,FRESH_YAW_GPIO,FRESH_PITCH_GPIO,pc_seen&&now-pc_seen<3000000?"true":"false",audio_busy?"true":"false",index_step+1,cycles);
    xSemaphoreGive(gate);
}
static bool integer(const cJSON *j,int min,int max,int *out) {if(!cJSON_IsNumber(j)||!isfinite(j->valuedouble)||j->valuedouble<min||j->valuedouble>max||floor(j->valuedouble)!=j->valuedouble)return false;*out=(int)j->valuedouble;return true;}
bool fresh_control_json(const cJSON *j) {
    const cJSON *a=cJSON_GetObjectItemCaseSensitive(j,"action");if(!cJSON_IsString(a))return false;
    if(!strcmp(a->valuestring,"nod")||!strcmp(a->valuestring,"shake"))return fresh_control_try_gesture(!strcmp(a->valuestring,"nod"),fresh_control_revision());
    if(!strcmp(a->valuestring,"stop")||!strcmp(a->valuestring,"track_on"))return fresh_control_action(a->valuestring,.15f,300);
    float speed=.15f;int ms=300,repeat=1,interval=0,n=0;fresh_step_t steps[32];int axes[32]={0};
    const cJSON *v=cJSON_GetObjectItemCaseSensitive(j,"repeat");if(v&&!integer(v,1,100,&repeat))return false;
    v=cJSON_GetObjectItemCaseSensitive(j,"interval_ms");if(v&&!integer(v,0,3600000,&interval))return false;
    const cJSON *array=cJSON_GetObjectItemCaseSensitive(j,"steps");
    if(!strcmp(a->valuestring,"sequence")){if(!cJSON_IsArray(array)||(n=cJSON_GetArraySize(array))<1||n>32)return false;}
    else {if(array||(strcmp(a->valuestring,"left")&&strcmp(a->valuestring,"right")&&strcmp(a->valuestring,"up")&&strcmp(a->valuestring,"down")))return false;n=1;}
    for(int i=0;i<n;++i){const cJSON *item=array?cJSON_GetArrayItem(array,i):j;const cJSON *act=cJSON_GetObjectItemCaseSensitive(item,"action");if(!cJSON_IsString(act))return false;
        v=cJSON_GetObjectItemCaseSensitive(item,"speed");speed=.15f;if(v){if(!cJSON_IsNumber(v)||!isfinite(v->valuedouble)||v->valuedouble<=0||v->valuedouble>.35)return false;speed=v->valuedouble;}
        v=cJSON_GetObjectItemCaseSensitive(item,"duration_ms");ms=300;if(v&&!integer(v,1,3600000,&ms))return false;
        if(!strcmp(act->valuestring,"up"))axes[i]=1;
        else if(!strcmp(act->valuestring,"down")){axes[i]=1;speed=-speed;}
        else if(!strcmp(act->valuestring,"left"))speed=-speed;else if(!strcmp(act->valuestring,"wait"))speed=0;else if(strcmp(act->valuestring,"right"))return false;
        steps[i]=(fresh_step_t){speed,ms};
    }return fresh_control_plan_axes(steps,axes,n,repeat,interval);
}
