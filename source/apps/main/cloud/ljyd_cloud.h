#ifndef LJYD_CLOUD_H
#define LJYD_CLOUD_H

#include "qm_spec_api.h"

/* 灵机平台产品身份。换产品改这里。 */
/*
 * 独立双舵机工程使用产品 PID 11885。URL 中的产品记录1635不是PID。
 * 产品密钥只保留在本机私有配置；共享源码包替换为占位模板。
 */
#define CONFIG_XJIANG_CLOUD_PID    11885
#define CONFIG_XJIANG_CLOUD_SECERT ""

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LJYD_CLOUD_EVENT_CONNECTED = 0,
    LJYD_CLOUD_EVENT_DISCONNECTED,
} ljyd_cloud_event_t;

typedef void (*ljyd_cloud_event_cb_t)(ljyd_cloud_event_t event, void *iot_handle, void *userdata);
typedef void (*ljyd_cloud_prop_cb_t)(qm_spec_property_t *property);

int ljyd_cloud_init(void);
void *ljyd_cloud_get_handle(void);
void ljyd_cloud_set_event_cb(ljyd_cloud_event_cb_t cb, void *userdata);
/* 属性下发。不设置则云只打日志。iot_control 在自己的 init 里挂上。 */
void ljyd_cloud_set_prop_cb(ljyd_cloud_prop_cb_t cb);
void ljyd_cloud_on_network_up(void);
void ljyd_cloud_on_network_down(void);
/* 返回 QM_EOK 表示云已接手解绑，等 RESET 事件再清配网。 */
int ljyd_cloud_request_reset(void);

#ifdef __cplusplus
}
#endif

#endif
