"""Retire broken proxy pools without interrupting unrelated streamed requests."""
from threading import Lock
import httpx


class _Pool:
    def __init__(self, transport):
        self.transport = transport
        self.users = 0
        self.retired = False


class _LeasedStream(httpx.SyncByteStream):
    def __init__(self, stream, release):
        self.stream = stream
        self.release = release
        self.closed = False

    def __iter__(self):
        yield from self.stream

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.stream.close()
            finally:
                self.release()


class RecoveringTransport(httpx.BaseTransport):
    """Rotate on connection failures; never silently replay a request (e.g. POST).

    A response keeps its pool alive until the stream closes. A retired pool is
    closed only after its last request/stream releases it.
    """
    def __init__(self, factory):
        self.factory = factory
        self.lock = Lock()
        self.pool = _Pool(factory())
        self.closed = False

    def _release(self, pool):
        with self.lock:
            pool.users -= 1
            close = pool.retired and pool.users == 0
        if close:
            pool.transport.close()

    def handle_request(self, request):
        with self.lock:
            if self.closed:
                raise RuntimeError('Transport is closed')
            if self.pool.retired:
                self.pool = _Pool(self.factory())
            pool = self.pool
            pool.users += 1
        try:
            response = pool.transport.handle_request(request)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError, httpx.PoolTimeout):
            with self.lock:
                pool.retired = True
            self._release(pool)
            raise
        except BaseException:
            self._release(pool)
            raise
        response.stream = _LeasedStream(response.stream, lambda: self._release(pool))
        return response

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            pool = self.pool
            close = not pool.retired and pool.users == 0
            pool.retired = True
        if close:
            pool.transport.close()
