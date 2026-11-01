"""Independent image/control lanes and persistent direct-LAN HTTP connections."""
from contextlib import contextmanager
import http.client
import threading
from urllib.parse import urlsplit


class ESPTransport:
    def __init__(self, split=True):
        self.image_lock = threading.RLock()
        self.control_lock = threading.RLock() if split else self.image_lock

    @contextmanager
    def request(self, control=False):
        with self.control_lock if control else self.image_lock:
            yield


def control_base(url, port=81):
    parts = urlsplit(url)
    host = parts.hostname
    if parts.scheme != 'http' or not host or parts.username:
        raise ValueError('Expected a local http:// device address')
    if ':' in host:
        host = '[' + host + ']'
    return f'http://{host}:{port}'


class LANClient:
    """One instance per worker. No proxies or automatic POST retries."""
    def __init__(self, timeout=1.5):
        self.timeout = timeout
        self.connection = None
        self.origin = None

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None

    def request(self, url, data=None, limit=1024*1024):
        parts = urlsplit(url)
        origin = (parts.hostname, parts.port or 80)
        if parts.scheme != 'http' or not parts.hostname or parts.username:
            raise ValueError('Expected a local HTTP address')
        if self.origin != origin:
            self.close()
        if self.connection is None:
            self.connection = http.client.HTTPConnection(*origin, timeout=self.timeout)
            self.origin = origin
        headers = {'Cache-Control': 'no-cache'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        try:
            self.connection.request('POST' if data is not None else 'GET',
                (parts.path or '/') + ('?' + parts.query if parts.query else ''),
                body=data, headers=headers)
            response = self.connection.getresponse()
            body = response.read(limit + 1)
            if len(body) > limit:
                raise ValueError('Response exceeds size limit')
            result = response.status, response.headers, body
            response.close()
            return result
        except Exception:
            self.close()
            raise
