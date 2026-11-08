import httpx
import pytest
from util.network.recovering_transport import RecoveringTransport
from util.common.diagnostics import redact_diagnostic


class Pool(httpx.BaseTransport):
    def __init__(self):
        self.closed = False
        self.calls = []

    def handle_request(self, request):
        self.calls.append(request.method)
        if request.url.path == '/fail':
            raise httpx.ConnectError('TLS failed', request=request)
        return httpx.Response(200, stream=httpx.ByteStream(b'ok'))

    def close(self):
        self.closed = True


def test_rotating_pool_preserves_inflight_stream_and_never_replays_post():
    pools = []

    def factory():
        pool = Pool()
        pools.append(pool)
        return pool

    transport = RecoveringTransport(factory)
    with httpx.Client(transport=transport) as client:
        stream = client.send(client.build_request('GET', 'https://test/ok'), stream=True)
        with pytest.raises(httpx.ConnectError):
            client.post('https://test/fail')
        assert pools[0].calls == ['GET', 'POST']
        assert not pools[0].closed
        assert client.get('https://test/ok').content == b'ok'
        assert len(pools) == 2
        assert stream.read() == b'ok'
        assert pools[0].closed
    assert all(pool.closed for pool in pools)


def test_repeated_failures_release_every_retired_pool():
    pools = []

    def factory():
        pools.append(Pool())
        return pools[-1]

    with httpx.Client(transport=RecoveringTransport(factory)) as client:
        for _ in range(200):
            with pytest.raises(httpx.ConnectError):
                client.get('https://test/fail')
        assert client.get('https://test/ok').status_code == 200
    assert len(pools) == 201
    assert all(pool.closed for pool in pools)


def test_redaction_covers_signed_urls_auth_headers_and_cookies():
    result = redact_diagnostic('HTTP 403 https://user:secret@cdn.test/private/key?sign=abc\nCookie: SESSDATA=private\nAuthorization: Bearer xyz')
    assert 'cdn.test' in result and 'HTTP 403' in result
    for secret in ['user', 'secret', 'private', 'abc', 'xyz']:
        assert secret not in result


def test_real_proxy_tls_failure_recovers_shared_client():
    import socketserver
    from threading import Thread

    class Tunnel(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(1)
            self.request.recv(8192)
            self.request.sendall(b'HTTP/1.1 200 Connection established\r\n\r\n')

    server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Tunnel)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    transport = RecoveringTransport(lambda: httpx.HTTPTransport(
        proxy=f'http://127.0.0.1:{server.server_address[1]}',
        limits=httpx.Limits(max_connections=2)))
    try:
        with httpx.Client(transport=transport, timeout=0.2) as client:
            for _ in range(6):
                with pytest.raises(httpx.ConnectError):
                    client.head('https://example.invalid/media')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_failure_record_is_bounded_and_round_trips_in_old_task_format():
    from dataclasses import asdict
    from util.download.task.info import DownloadInfo
    from util.common.diagnostics import failure_record
    record = failure_record({}, 'parse', 'PoolTimeout https://cdn.test/path?secret=abc ' + 'x' * 20000)
    assert record['category'] == 'connection_pool'
    assert len(record['message']) <= 16384
    assert 'abc' not in record['message']
    info = DownloadInfo()
    assert info.last_error == {}
    info.from_dict({'last_error': record})
    assert asdict(info)['last_error'] == record
