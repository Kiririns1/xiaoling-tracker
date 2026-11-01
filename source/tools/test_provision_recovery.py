from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'apps/main/cloud/ljyd_provision.c').read_text(encoding='utf-8')
recovery=source[source.index('static qm_work_t recovery_work;'):source.index('static char pending_ssid')]
startup=source[source.index('int ljyd_provision_init(void)'):]
stub=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef int qm_work_t;
#define QM_EOK 0
#define QM_EVENT_WIFI 1
#define QM_EVENT_ANY_ID -1
#define LOG_TAG "test"
#define QM_LOGI(...) ((void)0)
#define QM_LOGW(...) ((void)0)
#define QM_LOGE(...) ((void)0)
static int arms,cancels,reboots,ble_starts,registered,saved_wifi=99,pair_flag=1;
static uint8_t wifi_event_registered;
void ljyd_provision_pairing_and_reboot(void);
static int qm_post_delayed_action(qm_work_t *w,void(*f)(void*),void *arg,int ms){(void)w;(void)f;(void)arg;assert(ms==30000);++arms;return 0;}
static int qm_cancel_delayed_action(qm_work_t *w){(void)w;++cancels;return 0;}
static int qm_kv_set(const char *key,const void *value,int size,int save){assert(!strcmp(key,"cloud/pair_once")&&size==1&&save==1);pair_flag=*(const uint8_t*)value;return 0;}
static int qm_kv_del(const char *key){assert(!strcmp(key,"cloud/pair_once"));pair_flag=0;return 0;}
static void qm_msleep(int ms){assert(ms==100);}
static void qm_reboot(void){++reboots;}
static void provision_wifi_event_handler(void){}
static int qm_event_handler_register(int base,int id,void(*cb)(void),void *arg){(void)base;(void)id;(void)cb;(void)arg;++registered;return 0;}
static void provision_env_load(void){}
static int provision_start_ble(void){++ble_starts;return 0;}
static int wifi_starts;
static int provision_has_saved_wifi(void){return saved_wifi!=0;}
static int provision_start_wifi(void);
static int qm_kv_get(const char *key,void *value,int *size){assert(!strcmp(key,"cloud/pair_once")&&*size==1);*(uint8_t*)value=pair_flag;return 0;}
'''
recovery+='\nstatic int provision_start_wifi(void){++wifi_starts;arm_recovery();return 0;}\n'
checks=r'''
int main(void){
 pair_flag=0;
 assert(ljyd_provision_init()==0&&wifi_starts==1&&ble_starts==0&&saved_wifi==99);
 assert(ljyd_provision_init()==0&&wifi_starts==2&&registered==1);
 arm_recovery();arm_recovery();assert(arms==1&&recovery_pending);
 ljyd_provision_cloud_ready(1);assert(!recovery_pending&&cancels==1);
 wifi_online=1;recovery_timeout(NULL);assert(reboots==0);
 ljyd_provision_cloud_ready(0);assert(arms==1);
 wifi_online=0;
 ljyd_provision_cloud_ready(0);ljyd_provision_cloud_ready(0);assert(arms==2&&recovery_pending);
 recovery_timeout(NULL);assert(reboots==1&&pair_flag==1&&saved_wifi==99);
 assert(ljyd_provision_init()==0&&ble_starts==1&&pair_flag==0&&saved_wifi==99);
 saved_wifi=0;assert(ljyd_provision_init()==0&&ble_starts==2);
 puts("PASS: saved Wi-Fi reconnects automatically; explicit re-pair/missing config enters BLE; Wi-Fi failure deadline is not extended; cloud-only outage does not force pairing.");
}
'''
with tempfile.TemporaryDirectory(dir=root.parent/'tmp',prefix='pair_test_') as folder:
 p=Path(folder);(p/'test.c').write_text(stub+recovery+startup+checks,encoding='utf-8')
 subprocess.run(['C:/mingw64/bin/gcc.exe','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
