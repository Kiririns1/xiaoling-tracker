"""Bounded background posture control and acknowledgement channel."""
import json
import logging
import queue
import threading
import time
import uuid
from esp_transport import LANClient


class PostureLink:
    def __init__(self, base, transport):
        self.base, self.transport = base, transport
        self.queue = queue.Queue(maxsize=8)
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def enqueue(self, path, payload):
        try:
            self.queue.put_nowait((path, payload, time.monotonic()))
        except queue.Full:
            logging.warning('Posture queue full; request not sent')

    def action(self, action, state):
        if state.get('boot_id') is not None:
            self.enqueue('/api/posture', {'action': action, 'boot_id': state['boot_id']})

    def report(self, event, state):
        if state.get('boot_id') is not None:
            self.enqueue('/api/posture', {'event': event, 'boot_id': state['boot_id'],
                                         'event_id': uuid.uuid4().hex})

    def run(self):
        client = LANClient(timeout=.5)
        try:
            while not self.stopping.is_set():
                try:
                    path, payload, created = self.queue.get(timeout=.1)
                except queue.Empty:
                    continue
                try:
                    with self.transport.request(control=True):
                        if self.stopping.is_set() or time.monotonic()-created > 1.5:
                            continue
                        code, _, _ = client.request(self.base+path, data=json.dumps(payload).encode())
                    if code != 200:
                        logging.warning('Posture request rejected: HTTP %s', code)
                except Exception as exc:
                    logging.warning('Posture result unknown; not retried: %s', exc)
        finally:
            client.close()

    def close(self):
        self.stopping.set()
        self.thread.join(3)
