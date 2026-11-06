"""Bounded Range throughput measurement without task or account state changes."""
from concurrent.futures import ThreadPoolExecutor
import re
import time
import httpx


def benchmark(url, *, threads=4, buffer_size=8192, sample_bytes=32 * 1024 * 1024,
              headers=None, proxy=None, retries=1):
    if threads not in range(1, 11) or buffer_size not in (8192, 65536, 262144):
        raise ValueError("unsupported thread count or buffer size")
    if sample_bytes < threads or sample_bytes > 256 * 1024 * 1024 or retries not in range(3):
        raise ValueError("sample must be bounded and retries between 0 and 2")
    request_headers = {**(headers or {}), "Accept-Encoding": "identity"}
    limits = httpx.Limits(max_connections=threads, max_keepalive_connections=threads)
    with httpx.Client(headers=request_headers, proxy=proxy, trust_env=False,
                      limits=limits, timeout=httpx.Timeout(10, connect=15), follow_redirects=True) as client:
        # Probe one byte without reading an unbounded 200 response.
        with client.stream("GET", url, headers={"Range": "bytes=0-0"}) as response:
            match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
            if response.status_code != 206 or not match:
                raise ValueError("server does not support valid Range responses")
            total = int(match[1])
        size = min(sample_bytes, total)
        if size < threads:
            raise ValueError("resource too small")

        def download(index):
            start = size * index // threads
            end = size * (index + 1) // threads - 1
            received, retry_count = 0, 0
            while True:
                try:
                    with client.stream("GET", url, headers={"Range": f"bytes={start + received}-{end}"}) as response:
                        expected_range = f"bytes {start + received}-{end}/{total}"
                        if response.status_code != 206 or response.headers.get("Content-Range") != expected_range:
                            return received, retry_count, "invalid_range"
                        if response.headers.get("Content-Encoding", "identity") != "identity":
                            return received, retry_count, "encoded_response"
                        for chunk in response.iter_bytes(chunk_size=buffer_size):
                            received += len(chunk)
                            if received > end - start + 1:
                                return received, retry_count, "oversized_response"
                    if received == end - start + 1:
                        return received, retry_count, None
                    raise httpx.ReadError("incomplete response")
                except httpx.HTTPError as error:
                    if retry_count >= retries:
                        # Do not expose signed URLs or proxy credentials in error messages.
                        return received, retry_count, type(error).__name__
                    retry_count += 1

        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=threads) as pool:
            results = list(pool.map(download, range(threads)))
        elapsed = time.perf_counter() - started
    downloaded = sum(r[0] for r in results)
    return {"threads": threads, "buffer_size": buffer_size, "sample_bytes": size,
            "downloaded_bytes": downloaded, "seconds": round(elapsed, 3),
            "MiB_per_second": round(downloaded / elapsed / 1024 / 1024, 3),
            "retries": sum(r[1] for r in results), "errors": [r[2] for r in results if r[2]]}
