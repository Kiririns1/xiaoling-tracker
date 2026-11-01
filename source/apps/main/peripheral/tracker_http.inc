/* Included by fresh_http.c so all command admission shares frame history. */
static char follow_client[65];static unsigned follow_seq;static int64_t last_nod;
static cJSON *tracker_read_json(httpd_req_t *r,int limit){
 if(r->content_len<1||r->content_len>limit)return NULL;
 char *b=malloc(r->content_len+1);if(!b)return NULL;int n=0;
 while(n<r->content_len){int k=httpd_req_recv(r,b+n,r->content_len-n);if(k<=0){free(b);return NULL;}n+=k;}b[n]=0;
 cJSON *j=cJSON_ParseWithOpts(b,NULL,true);free(b);return j;
}
static bool tracker_fresh_frame(cJSON *j){
 unsigned id;bool valid=uint_value(cJSON_GetObjectItem(j,"frame_id"),&id);if(!valid)return false;
 xSemaphoreTake(raw_lock,portMAX_DELAY);bool fresh=fresh_frame_recent(&history,id,esp_timer_get_time());xSemaphoreGive(raw_lock);return fresh;
}
static esp_err_t tracker_follow_http(httpd_req_t *r){
 cJSON *j=tracker_read_json(r,512);if(!j)return httpd_resp_send_err(r,HTTPD_400_BAD_REQUEST,"Invalid command");
 bool nod=!strcmp(r->uri,"/api/fist-nod"),ok=false;
 unsigned boot=0,rev=0,s=0;const cJSON *client=cJSON_GetObjectItem(j,"client_id");
 cJSON *y=cJSON_GetObjectItem(j,"yaw"),*p=cJSON_GetObjectItem(j,"pitch");
 bool valid=uint_value(cJSON_GetObjectItem(j,"boot_id"),&boot)&&boot==tracker_boot_id()&&uint_value(cJSON_GetObjectItem(j,"revision"),&rev)&&uint_value(cJSON_GetObjectItem(j,"seq"),&s)&&cJSON_IsString(client)&&strlen(client->valuestring)>=8&&strlen(client->valuestring)<=64;
 if(valid&&!strcmp(follow_client,client->valuestring)&&s<=follow_seq)valid=false;
 bool moving=nod;
 if(!nod){valid=valid&&cJSON_IsNumber(y)&&cJSON_IsNumber(p)&&isfinite(y->valuedouble)&&isfinite(p->valuedouble)&&fabs(y->valuedouble)<=.030001&&fabs(p->valuedouble)<=.030001;
  moving=valid&&(fabs(y->valuedouble)+fabs(p->valuedouble)>=.001);}
 if(moving&&!tracker_fresh_frame(j))valid=false;
 if(nod){unsigned frames=0,ms=0;valid=valid&&uint_value(cJSON_GetObjectItem(j,"confirmed_frames"),&frames)&&frames>=6&&uint_value(cJSON_GetObjectItem(j,"held_ms"),&ms)&&ms>=600&&(!last_nod||esp_timer_get_time()-last_nod>=2000000);}
 if(valid)ok=nod?tracker_fist_nod(rev):tracker_follow(y->valuedouble,p->valuedouble,rev);
 if(ok){strcpy(follow_client,client->valuestring);follow_seq=s;if(nod)last_nod=esp_timer_get_time();}
 cJSON_Delete(j);httpd_resp_set_status(r,ok?(nod?"202 Accepted":"200 OK"):"409 Conflict");
 return json_reply(r,ok?"{\"accepted\":true}":"{\"accepted\":false,\"reason\":\"stale_busy_or_disabled\"}");
}
static esp_err_t tracker_light_http(httpd_req_t *r){
 if(r->method==HTTP_POST){cJSON *j=tracker_read_json(r,256);bool ok=tracker_light_request(j);cJSON_Delete(j);if(!ok){httpd_resp_set_status(r,"409 Conflict");return json_reply(r,"{\"accepted\":false}");}}
 char state[256];tracker_light_state(state,sizeof(state));return json_reply(r,state);
}
static esp_err_t tracker_track_compat(httpd_req_t *r){
 if(r->method==HTTP_GET)return json_reply(r,"{\"protocol\":\"tracking-only-v1\"}");
 cJSON *j=tracker_read_json(r,128),*d=cJSON_GetObjectItem(j,"direction");
 bool valid=cJSON_IsNumber(d)&&floor(d->valuedouble)==d->valuedouble&&d->valuedouble>=-1&&d->valuedouble<=1;
 bool ok=valid&&tracker_follow(d->valuedouble*.03,0,fresh_control_revision());cJSON_Delete(j);
 httpd_resp_set_status(r,ok?"200 OK":"409 Conflict");return json_reply(r,ok?"{\"accepted\":true}":"{\"accepted\":false}");
}
static esp_err_t tracker_posture_http(httpd_req_t *r){
 cJSON *j=tracker_read_json(r,512);unsigned boot=0;
 bool ok=uint_value(cJSON_GetObjectItem(j,"boot_id"),&boot)&&boot==tracker_boot_id();
 const cJSON *a=cJSON_GetObjectItem(j,"action"),*e=cJSON_GetObjectItem(j,"event"),*id=cJSON_GetObjectItem(j,"event_id");
 static char previous[33];static int64_t last_alert;
 if(ok&&cJSON_IsString(a))ok=tracker_posture_action(a->valuestring);
 else if(ok&&cJSON_IsString(e)&&cJSON_IsString(id)&&strlen(id->valuestring)==32){
  const char *names[]={"enabled","disabled","calibrating","calibrated","uncalibrated","monitoring","calibration_rejected","alert"};
  const char *texts[]={"坐姿检测已开启，请坐直后说校准坐姿。","坐姿检测已关闭。","正在校准，请保持坐直。","坐姿校准完成。","坐姿尚未校准，请坐直后说校准坐姿。","坐姿检测正在运行。","无法开始校准，请等镜头停稳，并让鼻子双眼和双肩进入画面。","请注意坐姿，坐直并保持头肩自然。"};
  int selected=-1;for(unsigned i=0;i<8;++i)if(!strcmp(e->valuestring,names[i]))selected=i;
  ok=selected>=0;
  if(ok&&selected!=1){char snapshot[1400];fresh_control_state(snapshot,sizeof(snapshot),false);cJSON *state=cJSON_Parse(snapshot);ok=cJSON_IsTrue(cJSON_GetObjectItem(state,"posture_enabled"));cJSON_Delete(state);}

  if(ok&&strcmp(previous,id->valuestring)){
   int64_t now=esp_timer_get_time();
   if(selected!=7||!last_alert||now-last_alert>=5000000){tracker_dialog_notify(texts[selected]);if(selected==7){last_alert=now;tracker_light_alert();}}
   strcpy(previous,id->valuestring);
  }
 }else ok=false;
 cJSON_Delete(j);httpd_resp_set_status(r,ok?"200 OK":"409 Conflict");
 return json_reply(r,ok?"{\"accepted\":true}":"{\"accepted\":false}");
}
static void tracker_routes(httpd_handle_t h){
 route(h,"/api/posture",HTTP_POST,tracker_posture_http);
 route(h,"/api/hand-follow",HTTP_POST,tracker_follow_http);route(h,"/api/fist-nod",HTTP_POST,tracker_follow_http);
 route(h,"/api/light",HTTP_GET,tracker_light_http);route(h,"/api/light",HTTP_POST,tracker_light_http);
 route(h,"/track",HTTP_GET,tracker_track_compat);route(h,"/track",HTTP_POST,tracker_track_compat);
}
