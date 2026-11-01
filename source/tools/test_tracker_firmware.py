"""Execute firmware C/C++ with fake PWM/time; no serial port or hardware access."""
from pathlib import Path
import subprocess,tempfile,ctypes,json
root=Path(__file__).resolve().parents[1]
src=root/'apps/main/peripheral'
cjson=Path(r'C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer/esp-idf/components/json/cJSON')
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    dll=tmp/'intent.dll'
    subprocess.run(['gcc','-shared','-o',str(dll),str(src/'tracker_intent.c')],check=True)
    class Intent(ctypes.Structure):
        _fields_=[('kind',ctypes.c_int),('level',ctypes.c_int),('wake_bytes',ctypes.c_size_t)]
    api=ctypes.CDLL(str(dll));api.tracker_parse.argtypes=[ctypes.c_char_p,ctypes.c_bool];api.tracker_parse.restype=Intent
    cases=[('你好小灵',False,1,-1),('你好小林',False,1,-1),('小林，开始追踪手。',False,3,-1),('开始追踪脸',False,4,-1),('停止追踪',False,5,-1),('停止聊天',True,2,-1),('调节亮度',False,7,-1),('亮度调整为5',False,8,5),('五',True,8,5),('十级',True,8,10),('0',True,8,0),('亮度调整为11',False,9,-1),('-1',True,9,-1),('5.5',True,9,-1),('亮度调整为五十五',False,9,-1),('取消',True,12,-1),('你好',False,0,-1),('五',False,0,-1),('不要开始追踪手',False,0,-1),('请开始追踪手',False,3,-1),('开灯',False,10,-1),('关灯',False,11,-1)]
    posture_cases=[('开启坐姿检测',13),('开始坐姿检测',13),('关闭坐姿检测',14),('停止坐姿检测',14),('校准坐姿',15),('重新校准坐姿',15),('暂停坐姿追脸',16),('恢复坐姿追脸',17),('查询坐姿状态',18),('旋转画面',19),('退出电脑程序',20)]
    for text,kind in posture_cases:
        cases.extend([(text,False,kind,-1),('你好小灵，'+text+'。',False,kind,-1)])
    cases.extend([('不要开启坐姿检测',False,0,-1),('如何校准坐姿',False,0,-1),('退出聊天',False,2,-1)])
    for text,waiting,kind,level in cases:
        result=api.tracker_parse(text.encode(),waiting)
        assert (result.kind,result.level)==(kind,level),(text,result.kind,result.level)
    import _ctypes
    _ctypes.FreeLibrary(api._handle)
    code=(src/'tracker_control.cpp').read_text(encoding='utf-8')
    code='\n'.join(line for line in code.splitlines() if not any(x in line for x in ['#include "driver/','#include "esp_','#include "freertos/']))
    stubs=r'''
#include <stdint.h>
#include <assert.h>
#include <math.h>
typedef void* SemaphoreHandle_t;typedef void* esp_timer_handle_t;
typedef int ledc_channel_t;
struct ledc_timer_config_t{int speed_mode,timer_num,duty_resolution,freq_hz,clk_cfg;};
struct ledc_channel_config_t{int gpio_num,speed_mode,channel,timer_sel,duty;};
struct esp_timer_create_args_t{void(*callback)(void*);const char *name;};
enum {LEDC_CHANNEL_4=4,LEDC_CHANNEL_5=5,LEDC_LOW_SPEED_MODE=0,LEDC_TIMER_2=2,LEDC_TIMER_14_BIT=14,LEDC_AUTO_CLK=0};
#define ESP_OK 0
#define pdTRUE 1
#define portMAX_DELAY 0
static int64_t fake_now=1000000;static unsigned pwm[8];
static int64_t esp_timer_get_time(){return fake_now;}
static unsigned esp_random(){return 123;}
static void* xSemaphoreCreateMutex(){return (void*)1;}
static int xSemaphoreTake(void*,int){return 1;}
static void xSemaphoreGive(void*){}
static int ledc_stop(int,int ch,int){pwm[ch]=0;return 0;}
static int ledc_set_duty(int,int ch,unsigned d){pwm[ch]=d;return 0;}
static int ledc_update_duty(int,int){return 0;}
static int ledc_timer_config(ledc_timer_config_t*){return 0;}
static int ledc_channel_config(ledc_channel_config_t*){return 0;}
static int esp_timer_create(esp_timer_create_args_t*,void** p){*p=(void*)1;return 0;}
static int esp_timer_start_periodic(void*,int){return 0;}
'''
    checks=r'''
int main(){
 assert(fresh_control_init());assert(tracker_boot_id()==123);assert(!tracking);
 assert(!tracker_follow(.03,0,revision));assert(pwm[4]==0);
 assert(tracker_select("hand",true));unsigned r=revision;
 assert(tracker_follow(.03,-.03,r));assert(pwm[4]==1425*16383/20000);assert(pwm[5]==1575*16383/20000);
 fake_now+=100000;tick(nullptr);assert(pwm[4]==1500*16383/20000);assert(pwm[5]==1500*16383/20000);
 assert(!tracker_follow(.03,-.03,r));fake_now+=150000;tick(nullptr);assert(!pwm[4]&&!pwm[5]);
 fake_now+=50000;assert(tracker_follow(.03,0,r));
 assert(tracker_select("face",true));assert(!pwm[4]&&!pwm[5]);assert(!tracker_follow(.03,0,r));
 assert(!tracker_fist_nod(revision));assert(tracker_select("hand",true));
 assert(tracker_fist_nod(revision));assert(settling);fake_now+=199000;tick(nullptr);assert(!pwm[5]);
 fake_now+=1000;tick(nullptr);assert(gesture.busy());assert(current.pitch==-.025f);
 fake_now+=300000;tick(nullptr);assert(current.pitch==0);fake_now+=200000;tick(nullptr);assert(current.pitch==.025f);
 fake_now+=300000;tick(nullptr);assert(!gesture.busy()&&!pwm[5]);
 assert(fresh_control_action("stop",.07,300));assert(!tracking&&!pwm[4]&&!pwm[5]);
 assert(!tracker_follow(.03,0,revision));assert(tracker_select("hand",true));
 fresh_control_audio(true);assert(!tracker_follow(.03,0,revision));fresh_control_audio(false);
 fake_now+=3000001;tick(nullptr);assert(!tracking&&!pwm[4]&&!pwm[5]);
 char request[200];snprintf(request,sizeof(request),"{\"action\":\"stop\",\"expected_tracking_revision\":%u}",tracking_revision);
 cJSON *cmd=cJSON_Parse(request);assert(tracker_select("face",true));assert(!fresh_control_json(cmd)&&tracking);cJSON_Delete(cmd);
 assert(!fresh_control_action("left",.07,501));assert(!tracker_follow(NAN,0,revision));
 assert(tracker_posture_action("posture_on"));assert(posture_enabled&&tracking&&selected_mode==1);
 unsigned before=posture_calibration;assert(tracker_posture_action("posture_calibrate"));assert(posture_calibration==before+1);
 assert(tracker_posture_action("posture_pause"));assert(posture_enabled&&!tracking);
 assert(tracker_posture_action("posture_resume"));assert(tracking);
 fake_now+=3000001;tick(nullptr);assert(!tracking&&posture_enabled&&!pwm[4]&&!pwm[5]);
 assert(tracker_posture_action("posture_status"));assert(posture_query==1);
 assert(tracker_posture_action("posture_rotate"));assert(posture_rotation==1);
 assert(tracker_select("hand",true));assert(!posture_enabled&&tracking);
 assert(!tracker_posture_action("posture_calibrate"));
 assert(tracker_posture_action("posture_on"));assert(tracker_posture_action("posture_off"));assert(!posture_enabled&&!tracking);
 assert(tracker_posture_action("posture_on"));assert(tracker_posture_action("posture_exit"));assert(!posture_enabled&&!tracking&&posture_exit==1);
 char state[1200];fresh_control_state(state,sizeof(state),true);assert(strstr(state,"facetracker-dual-step-v1"));
 cJSON *snapshot=cJSON_Parse(state);assert(snapshot);assert(cJSON_GetObjectItem(snapshot,"posture_exit")->valueint==1);cJSON_Delete(snapshot);
 revision=boot_id=tracking_revision=posture_calibration=posture_query=posture_rotation=posture_exit=4294967295U;
 fresh_control_state(state,sizeof(state),false);snapshot=cJSON_Parse(state);assert(snapshot);cJSON_Delete(snapshot);
 puts("actual tracker PWM/timing/state checks passed");
}
'''
    harness=tmp/'tracker.cpp';harness.write_text(stubs+code+checks,encoding='utf-8')
    obj=tmp/'cjson.o'
    subprocess.run(['gcc','-c',str(cjson/'cJSON.c'),'-o',str(obj)],check=True)
    exe=tmp/'tracker.exe'
    subprocess.run(['g++','-std=c++17','-I'+str(src),'-I'+str(cjson),str(harness),str(obj),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
    print(json.dumps({'intent_cases':len(cases),'motion':'passed','hardware':'not accessed'}))
