"""ESP JPEG snapshots -> OpenCV. Q quits; R rotates; S saves raw frame."""
import argparse
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from esp_transport import ESPTransport, LANClient


def camera_url(address):
    address = address.strip()
    if '://' not in address:
        address = 'http://' + address
    parts = urlsplit(address)
    if parts.scheme != 'http' or not parts.hostname or parts.username:
        raise ValueError('Enter the ESP local IP, e.g. 192.168.43.123')
    return f'http://{parts.netloc}/frame.jpg'


class Camera:
    def __init__(self, url, fps=10, quality=55, transport=None):
        if not 1 <= fps <= 30 or quality not in (55, 70, 85):
            raise ValueError('fps must be 1..30; quality must be 55, 70 or 85')
        self.transport = transport if transport is not None else ESPTransport()
        self.url, self.period = url, 1 / fps
        self.quality = quality
        self.last_frame_id = None
        self.fetched_frame_id = None
        self.image_frame_id = None
        self.fetch_ms = 0
        self.frame_age_ms = 0
        self.fetched_capture_time = 0
        self.captured_at = 0
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.frame = None
        self.updated = 0
        self.number = 0
        self.status = 'Connecting...'
        # Direct LAN connection: do not send camera requests through system proxies.
        self.client = LANClient(timeout=2)
        self.thread = threading.Thread(target=self.run, daemon=True)

    def fetch(self):
        import cv2
        import numpy as np
        # No after cursor: frame counters can restart when the ESP reboots.
        started = time.monotonic()
        with self.transport.request():
            code, headers, data = self.client.request(self.url + f'?q={self.quality}&t={time.time_ns()}')
        if code == 204:
            return None
        if code != 200:
            raise RuntimeError(f'ESP {code}: {data[:160].decode("utf-8", "replace")}')
        if headers.get_content_type() != 'image/jpeg':
            raise ValueError('ESP response is not a JPEG image')
        frame_id = headers.get('X-Frame-Id')
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('JPEG decode failed')
        self.fetch_ms = (time.monotonic() - started) * 1000
        # Conservative upper age bound: header age plus the entire request.
        # Do not treat arrival time as capture time, especially on slow Wi-Fi.
        self.frame_age_ms = max(0., float(headers.get('X-Frame-Age-Ms', '0'))) + self.fetch_ms
        self.fetched_capture_time = time.monotonic() - self.frame_age_ms/1000
        if frame_id is not None and frame_id == self.last_frame_id:
            return None
        self.last_frame_id = frame_id
        self.fetched_frame_id = frame_id
        return frame

    def run(self):
        while not self.stop.is_set():
            started = time.monotonic()
            wait = self.period
            try:
                frame = self.fetch()
                if frame is not None:
                    with self.lock:
                        self.frame = frame
                        self.updated = time.monotonic()
                        self.image_frame_id = self.fetched_frame_id
                        self.captured_at = self.fetched_capture_time
                        self.number += 1
                        self.status = 'Live'
            except Exception as exc:
                self.last_frame_id = None
                message = str(exc)
                if isinstance(exc, urllib.error.HTTPError) and exc.code == 503:
                    detail = exc.read(512).decode('utf-8', errors='replace')
                    message = 'ESP 503: ' + detail
                with self.lock:
                    if self.status != message:
                        print('[Camera]', message, flush=True)
                    self.status = message
                wait = .2
            self.stop.wait(max(0, wait - (time.monotonic() - started)))
        self.client.close()



def main():
    from pc_runtime import main as run
    run()


if __name__ == '__main__':
    main()
