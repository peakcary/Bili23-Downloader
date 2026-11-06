from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import re
import pytest
from util.download_benchmark import benchmark


@pytest.fixture
def range_server():
    class Handler(BaseHTTPRequestHandler):
        ignore_range = False
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.ignore_range:
                self.send_response(200)
                self.end_headers()
                return
            start, end = map(int, re.fullmatch(r'bytes=(\d+)-(\d+)', self.headers['Range']).groups())
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/1048576')
            self.send_header('Content-Length', str(end-start+1))
            self.end_headers()
            self.wfile.write(b'x'*(end-start+1))
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/media', Handler
    server.shutdown()
    server.server_close()
    thread.join()


def test_benchmark_covers_exact_sample(range_server):
    url, _ = range_server
    result = benchmark(url, threads=6, buffer_size=65536, sample_bytes=100001)
    assert result['downloaded_bytes'] == 100001
    assert result['errors'] == []
    assert result['retries'] == 0


def test_benchmark_rejects_ignored_range(range_server):
    url, handler = range_server
    handler.ignore_range = True
    with pytest.raises(ValueError, match='Range'):
        benchmark(url)


def test_benchmark_rejects_unbounded_sample():
    with pytest.raises(ValueError):
        benchmark('http://unused', sample_bytes=1024**3)
