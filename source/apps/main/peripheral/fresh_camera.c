#include "bsp_camera.h"
#include "fresh_http.h"
#include "driver/i2c_master.h"
#include "driver/gpio.h"
#include "esp_cam_ctlr_spi.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdatomic.h>
typedef struct {uint8_t reg,val;} bf3901_reginfo_t;
#define BF3901_REG_DELAY 0xFE
#define YUV422_UYVY 0x02
#include "fresh_sensor_settings.h"
static esp_cam_ctlr_handle_t camera;
static i2c_master_bus_handle_t sensor_bus;
static i2c_master_dev_handle_t sensor;
static bool initialized,running;
static atomic_uint frames;
static const uint8_t frame_header[]={0xff,0xff,0xff,0};
static const uint8_t line_header[]={0xff,0xff,0xff,0x40};
static const esp_cam_sensor_spi_frame_info info={
 .frame_size=(240*2+6)*320+4,.line_size=240*2+6,
 .frame_header_check=frame_header,.line_header_check=line_header,
 .frame_header_check_size=4,.line_header_check_size=4,
 .frame_header_size=4,.line_header_size=6,.drop_frame_count=1
};
static esp_err_t reg_write(uint8_t reg,uint8_t value){uint8_t b[]={reg,value};return i2c_master_transmit(sensor,b,2,100);}
static esp_err_t sensor_configure(void){
 esp_err_t ret=reg_write(0x12,0x80);if(ret!=ESP_OK)return ret;vTaskDelay(pdMS_TO_TICKS(20));
 for(unsigned i=0;i<sizeof(bf3901_spi_1bit_24Minput_240x320_yuv422_uyvy_15fps)/sizeof(bf3901_reginfo_t);++i){bf3901_reginfo_t s=bf3901_spi_1bit_24Minput_240x320_yuv422_uyvy_15fps[i];if(s.reg==BF3901_REG_DELAY)vTaskDelay(pdMS_TO_TICKS(s.val));else if((ret=reg_write(s.reg,s.val))!=ESP_OK)return ret;}
 return ESP_OK;
}
static bool IRAM_ATTR received(esp_cam_ctlr_handle_t handle,esp_cam_ctlr_trans_t *trans,void *arg){
 (void)handle;(void)arg;
 /* Auto decode invokes this callback on its task, after checking headers. */
 if(trans->buffer&&trans->received_size==240*320*2){fresh_http_frame(trans->buffer,trans->received_size);atomic_fetch_add(&frames,1);}
 return false;
}
static void camera_health(void *unused){(void)unused;unsigned last=0,retries=0;
 for(;;){vTaskDelay(pdMS_TO_TICKS(5000));unsigned n=atomic_load(&frames);ESP_LOGI("fresh_camera","decoded=%u fps=%.1f",n,(n-last)/5.0f);
  if(n==last&&retries++<3){uint8_t reg=9,value=0;esp_err_t r=i2c_master_transmit_receive(sensor,&reg,1,&value,1,100);ESP_LOGW("fresh_camera","no frames; sensor standby=%02x read=%d; restart sensor",value,r);
   if(sensor_configure()==ESP_OK)reg_write(9,3);
  }last=n;}
}
esp_err_t bsp_camera_early_init(void){
 if(initialized)return ESP_OK;
 gpio_config_t pin={.pin_bit_mask=1ULL<<41,.mode=GPIO_MODE_OUTPUT};
 ESP_ERROR_CHECK(gpio_config(&pin));gpio_set_level(41,1);vTaskDelay(pdMS_TO_TICKS(20));gpio_set_level(41,0);vTaskDelay(pdMS_TO_TICKS(50));
 i2c_master_bus_config_t bus={.i2c_port=I2C_NUM_0,.sda_io_num=21,.scl_io_num=47,.clk_source=I2C_CLK_SRC_DEFAULT,.glitch_ignore_cnt=7,.flags.enable_internal_pullup=true};
 esp_err_t ret=i2c_new_master_bus(&bus,&sensor_bus);if(ret!=ESP_OK)return ret;
 i2c_device_config_t dev={.dev_addr_length=I2C_ADDR_BIT_LEN_7,.device_address=0x6e,.scl_speed_hz=100000};
 ret=i2c_master_bus_add_device(sensor_bus,&dev,&sensor);if(ret!=ESP_OK)return ret;
 uint8_t id[2];for(int i=0;i<2;++i){uint8_t r=0xfc+i;ret=i2c_master_transmit_receive(sensor,&r,1,&id[i],1,100);if(ret!=ESP_OK)return ret;}
 if(id[0]!=0x39||id[1]!=1){ESP_LOGE("fresh_camera","unexpected sensor %02x%02x",id[0],id[1]);return ESP_ERR_NOT_FOUND;}
 for(unsigned i=0;i<sizeof(bf3901_spi_1bit_24Minput_240x320_yuv422_uyvy_15fps)/sizeof(bf3901_reginfo_t);++i){bf3901_reginfo_t r=bf3901_spi_1bit_24Minput_240x320_yuv422_uyvy_15fps[i];if(r.reg==BF3901_REG_DELAY)vTaskDelay(pdMS_TO_TICKS(r.val));else if((ret=reg_write(r.reg,r.val))!=ESP_OK)return ret;}
 esp_cam_ctlr_spi_config_t cfg={.intf=ESP_CAM_CTLR_SPI_CAM_INTF_SPI,.io_mode=ESP_CAM_CTLR_SPI_CAM_IO_MODE_1BIT,.spi_port=SPI2_HOST,.spi_cs_pin=4,.spi_sclk_pin=13,.spi_data0_io_pin=8,.spi_data1_io_pin=-1,.spi_data2_io_pin=-1,.spi_data3_io_pin=-1,.reset_pin=-1,.pwdn_pin=-1,.h_res=240,.v_res=320,.input_data_color_type=CAM_CTLR_COLOR_YUV422,.frame_info=&info,.frame_buffer_count=2};
 ret=esp_cam_new_spi_ctlr(&cfg,&camera);if(ret!=ESP_OK)return ret;
 const void *backup=NULL;ret=esp_cam_ctlr_get_frame_buffer(camera,1,&backup);if(ret!=ESP_OK)return ret;
 esp_cam_ctlr_evt_cbs_t cb={.on_trans_finished=received};ret=esp_cam_ctlr_register_event_callbacks(camera,&cb,NULL);if(ret!=ESP_OK)return ret;
 ret=esp_cam_ctlr_enable(camera);if(ret!=ESP_OK)return ret;
 initialized=true;ESP_LOGI("fresh_camera","BF3901 original 22:29 register table loaded");return ESP_OK;
}
esp_err_t bsp_camera_stream_start(void){
 if(running)return ESP_OK;
 esp_err_t ret=fresh_http_start();if(ret!=ESP_OK)return ret;
 if(!initialized)return ESP_ERR_INVALID_STATE;
 /* Reinitialize after network startup; BF3901 may not resume clocks reliably
  * from the standby configured before Wi-Fi initialization. */
 ret=sensor_configure();if(ret!=ESP_OK)return ret;
 ret=esp_cam_ctlr_start(camera);if(ret!=ESP_OK)return ret;
 ret=reg_write(9,3);if(ret!=ESP_OK){esp_cam_ctlr_stop(camera);return ret;}
 running=true;xTaskCreate(camera_health,"camera_health",3072,NULL,1,NULL);return ESP_OK;
}
esp_err_t bsp_camera_start(void){esp_err_t ret=bsp_camera_early_init();return ret==ESP_OK?bsp_camera_stream_start():ret;}
bool bsp_camera_is_available(void){return initialized;}
