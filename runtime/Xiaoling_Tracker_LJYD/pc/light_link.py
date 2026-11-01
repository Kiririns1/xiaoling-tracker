"""Bounded background light requests. Never retry ambiguous toggle requests."""
import json
import logging
import queue
import threading
import time
import uuid
from esp_transport import LANClient

class LightLink:
    def __init__(self,base,transport):
        self.base=base;self.transport=transport;self.queue=queue.Queue(maxsize=8)
        self.stopping=threading.Event();self.thread=threading.Thread(target=self.run,daemon=True)
    def send(self,action,boot_id,percent=None):
        payload={'action':action,'event_id':uuid.uuid4().hex,'boot_id':boot_id}
        if percent is not None:payload['percent']=percent
        try:self.queue.put_nowait((payload,time.monotonic()))
        except queue.Full:logging.warning('[灯] 队列已满，请重新做手势')
    def run(self):
        client=LANClient(timeout=.5)
        try:
            while not self.stopping.is_set():
                try:payload,created=self.queue.get(timeout=.1)
                except queue.Empty:continue
                try:
                    with self.transport.request(control=True):
                        if self.stopping.is_set() or time.monotonic()-created>.7:continue
                        code,_,body=client.request(self.base+'/api/light',data=json.dumps(payload).encode())
                    logging.info('[灯] HTTP %s %s',code,body.decode('utf-8','replace'))
                except Exception as e:logging.warning('[灯] 请求结果未知，不自动重试: %s',e)
        finally:client.close()
    def close(self):self.stopping.set();self.thread.join(3)
