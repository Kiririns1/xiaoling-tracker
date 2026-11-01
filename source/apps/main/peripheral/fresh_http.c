#include "fresh_http.h"
#include "fresh_control.h"
#include "tracker_light.h"
#include "tracker_dialog.h"
#include "fresh_frame_guard.h"
#include "agent_app.h"
#include "esp_http_server.h"
#include "esp_jpeg_enc.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/idf_additions.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "lwip/tcp.h"
#include <math.h>
#include <limits.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#define RAW (240*320*2)
#define JPEG_CAP (128*1024)
static SemaphoreHandle_t raw_lock,jpg_lock;
static uint8_t *raw,*encode_input,*encode_output,*jpg,*http_buffer;
static unsigned seq,jpg_seq;static int jpg_len;
static fresh_frame_history_t history;
static int64_t capture_us,jpg_us;
static jpeg_enc_handle_t encoder;
static atomic_int quality=55;
static atomic_uint last_request;
static httpd_handle_t web,control_web;
esp_err_t fresh_http_enable_ap(void){
 if(!esp_netif_get_handle_from_ifkey("WIFI_AP_DEF")&&!esp_netif_create_default_wifi_ap())return ESP_FAIL;
 wifi_mode_t mode;esp_err_t ret=esp_wifi_get_mode(&mode);if(ret!=ESP_OK)return ret;
 if(mode!=WIFI_MODE_APSTA){ret=esp_wifi_set_mode(WIFI_MODE_APSTA);if(ret!=ESP_OK)return ret;}
 wifi_config_t cfg={.ap={.ssid="",.password="",.ssid_len=0,.max_connection=2,.authmode=WIFI_AUTH_WPA2_PSK}};
 return esp_wifi_set_config(WIFI_IF_AP,&cfg);
}
#include "fresh_page_generated.h"
void fresh_http_frame(const uint8_t *data,unsigned n){if(n!=RAW||!raw_lock)return;if(xSemaphoreTake(raw_lock,0)==pdTRUE){memcpy(raw,data,n);++seq;capture_us=esp_timer_get_time();fresh_frame_record(&history,seq,capture_us);xSemaphoreGive(raw_lock);}}
static void jpeg_worker(void *unused){(void)unused;unsigned last=0;
 for(;;){vTaskDelay(pdMS_TO_TICKS(80));if((unsigned)(esp_timer_get_time()/1000)-atomic_load(&last_request)>2000)continue;
  if(xSemaphoreTake(raw_lock,pdMS_TO_TICKS(10))!=pdTRUE){continue;}
  unsigned n=seq;int64_t at=capture_us;bool fresh=n&&n!=last&&esp_timer_get_time()-at<1000000;if(fresh)memcpy(encode_input,raw,RAW);xSemaphoreGive(raw_lock);if(!fresh)continue;last=n;
  for(int i=0;i<RAW;i+=2){uint8_t b=encode_input[i];encode_input[i]=encode_input[i+1];encode_input[i+1]=b;}
  jpeg_enc_set_quality(encoder,atomic_load(&quality));int bytes=0;if(jpeg_enc_process(encoder,encode_input,RAW,encode_output,JPEG_CAP,&bytes)!=JPEG_ERR_OK||bytes<=0||bytes>JPEG_CAP)continue;
  xSemaphoreTake(jpg_lock,portMAX_DELAY);memcpy(jpg,encode_output,bytes);jpg_len=bytes;jpg_seq=n;jpg_us=at;xSemaphoreGive(jpg_lock);
 }
}
static esp_err_t json_reply(httpd_req_t *r,const char *s){httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");return httpd_resp_sendstr(r,s);}
static esp_err_t home(httpd_req_t *r){httpd_resp_set_type(r,"text/html; charset=utf-8");return httpd_resp_sendstr(r,page);}
static esp_err_t camera_status(httpd_req_t *r){char b[200];xSemaphoreTake(raw_lock,portMAX_DELAY);snprintf(b,sizeof(b),"{\"have_image\":%s,\"frame_id\":%u,\"age_ms\":%lu,\"control_port\":81,\"pid\":11885}",seq&&esp_timer_get_time()-capture_us<1000000?"true":"false",seq,(unsigned long)((esp_timer_get_time()-capture_us)/1000));xSemaphoreGive(raw_lock);return json_reply(r,b);}
static esp_err_t frame(httpd_req_t *r){char q[96],v[20];unsigned after=0;int wanted=55;
 if(httpd_req_get_url_query_str(r,q,sizeof(q))==ESP_OK){if(httpd_query_key_value(q,"after",v,sizeof(v))==ESP_OK)after=strtoul(v,NULL,10);if(httpd_query_key_value(q,"q",v,sizeof(v))==ESP_OK)wanted=atoi(v);}
 if(wanted!=55&&wanted!=70&&wanted!=85){wanted=55;}
 atomic_store(&quality,wanted);atomic_store(&last_request,(unsigned)(esp_timer_get_time()/1000));
 bool is_raw=!strncmp(r->uri,"/frame.raw",10);SemaphoreHandle_t lock=is_raw?raw_lock:jpg_lock;xSemaphoreTake(lock,portMAX_DELAY);unsigned n=is_raw?seq:jpg_seq;int64_t at=is_raw?capture_us:jpg_us;int len=is_raw?RAW:jpg_len;bool fresh=n&&esp_timer_get_time()-at<1000000;if(fresh&&n!=after)memcpy(http_buffer,is_raw?raw:jpg,len);xSemaphoreGive(lock);
 if(!fresh){httpd_resp_set_status(r,"503 Service Unavailable");return httpd_resp_sendstr(r,"No recent valid frame; retry");}
 if(after==n){httpd_resp_set_status(r,"204 No Content");return httpd_resp_send(r,NULL,0);}
 snprintf(v,sizeof(v),"%u",n);httpd_resp_set_hdr(r,"X-Frame-Id",v);char age[24];snprintf(age,sizeof(age),"%lu",(unsigned long)((esp_timer_get_time()-at)/1000));httpd_resp_set_hdr(r,"X-Frame-Age-Ms",age);httpd_resp_set_hdr(r,"Cache-Control","no-store");httpd_resp_set_hdr(r,"X-Pixel-Format",is_raw?"UYVY":"JPEG");httpd_resp_set_type(r,is_raw?"application/octet-stream":"image/jpeg");return httpd_resp_send(r,(char*)http_buffer,len);
}
static bool uint_value(cJSON *v,unsigned *out){if(!cJSON_IsNumber(v)||!isfinite(v->valuedouble)||v->valuedouble<1||v->valuedouble>UINT_MAX||floor(v->valuedouble)!=v->valuedouble)return false;*out=(unsigned)v->valuedouble;return true;}
static esp_err_t control(httpd_req_t *r){char state[1200];if(r->method==HTTP_GET){fresh_control_state(state,sizeof(state),true);return json_reply(r,state);}
 if(r->content_len<1||r->content_len>4096)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid length");
 char *body=malloc(r->content_len+1);if(!body)return httpd_resp_send_err(r,HTTPD_500_INTERNAL_SERVER_ERROR,"No memory");int n=0;while(n<r->content_len){int k=httpd_req_recv(r,body+n,r->content_len-n);if(k<=0){free(body);return ESP_FAIL;}n+=k;}body[n]=0;cJSON *j=cJSON_Parse(body);free(body);if(!cJSON_IsObject(j)){cJSON_Delete(j);return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid JSON");}
 bool ok=false;double speed=0;const char *reason="invalid_action";
 if(!strcmp(r->uri,"/api/servo")){cJSON *s=cJSON_GetObjectItem(j,"speed");unsigned revision=0,frame_id=0;bool valid=uint_value(cJSON_GetObjectItem(j,"revision"),&revision);bool has_frame=uint_value(cJSON_GetObjectItem(j,"frame_id"),&frame_id);xSemaphoreTake(raw_lock,portMAX_DELAY);bool fresh=has_frame&&fresh_frame_recent(&history,frame_id,esp_timer_get_time());xSemaphoreGive(raw_lock);
  if(!valid)reason="invalid_revision";
  else if(!cJSON_IsNumber(s)||!isfinite(s->valuedouble)||fabs(s->valuedouble)>.35)reason="invalid_speed";
  else if(s->valuedouble!=0&&!fresh)reason="stale_frame";
  else{speed=s->valuedouble;reason=fresh_control_step_error(speed,revision);ok=reason==NULL;}}
 else ok=fresh_control_json(j);
 cJSON_Delete(j);if(!ok){char current[1200],response[1400];fresh_control_state(current,sizeof(current),false);snprintf(response,sizeof(response),"{\"accepted\":false,\"reason\":\"%s\",\"state\":%s}",reason?reason:"rejected",current);httpd_resp_set_status(r,"409 Conflict");return json_reply(r,response);}snprintf(state,sizeof(state),"{\"accepted\":true,\"speed\":%.3f}",speed);return json_reply(r,state);
}
static esp_err_t open_socket(httpd_handle_t h,int fd){(void)h;int one=1;return setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one))==0?ESP_OK:ESP_FAIL;}
static esp_err_t route(httpd_handle_t h,const char *uri,httpd_method_t method,esp_err_t(*fn)(httpd_req_t*)){httpd_uri_t u={.uri=uri,.method=method,.handler=fn};return httpd_register_uri_handler(h,&u);}
#include "tracker_http.inc"
esp_err_t fresh_http_start(void){if(web)return ESP_OK;
 raw_lock=xSemaphoreCreateMutex();jpg_lock=xSemaphoreCreateMutex();raw=heap_caps_malloc(RAW,MALLOC_CAP_SPIRAM);encode_input=heap_caps_aligned_alloc(16,RAW,MALLOC_CAP_SPIRAM);encode_output=heap_caps_aligned_alloc(16,JPEG_CAP,MALLOC_CAP_SPIRAM);jpg=heap_caps_malloc(JPEG_CAP,MALLOC_CAP_SPIRAM);http_buffer=heap_caps_malloc(RAW,MALLOC_CAP_SPIRAM);if(!raw_lock||!jpg_lock||!raw||!encode_input||!encode_output||!jpg||!http_buffer)return ESP_ERR_NO_MEM;
 jpeg_enc_config_t cfg=DEFAULT_JPEG_ENC_CONFIG();cfg.width=240;cfg.height=320;cfg.quality=55;cfg.task_enable=false;if(jpeg_enc_open(&cfg,&encoder)!=JPEG_ERR_OK)return ESP_FAIL;
 httpd_config_t c=HTTPD_DEFAULT_CONFIG();c.task_caps=MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT;c.open_fn=open_socket;c.max_uri_handlers=24;c.max_open_sockets=3;c.stack_size=8192;c.task_priority=3;c.lru_purge_enable=true;c.send_wait_timeout=2;c.recv_wait_timeout=2;esp_err_t ret=httpd_start(&web,&c);if(ret!=ESP_OK)return ret;
 route(web,"/",HTTP_GET,home);route(web,"/frame.jpg",HTTP_GET,frame);route(web,"/frame.raw",HTTP_GET,frame);route(web,"/api/camera",HTTP_GET,camera_status);route(web,"/api/control",HTTP_GET,control);route(web,"/api/control",HTTP_POST,control);route(web,"/api/servo",HTTP_POST,control);
 tracker_routes(web);
 c.server_port=81;c.ctrl_port=32769;c.stack_size=6144;c.task_priority=4;ret=httpd_start(&control_web,&c);if(ret!=ESP_OK)return ret;route(control_web,"/api/control",HTTP_GET,control);route(control_web,"/api/control",HTTP_POST,control);route(control_web,"/api/servo",HTTP_POST,control);route(control_web,"/api/camera",HTTP_GET,camera_status);
 tracker_routes(control_web);
 if(xTaskCreatePinnedToCoreWithCaps(jpeg_worker,"fresh_jpeg",16384,NULL,2,NULL,1,MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)!=pdPASS){return ESP_ERR_NO_MEM;}
 ESP_LOGI("fresh_http","preview :80, control :81 ready");return ESP_OK;
}
