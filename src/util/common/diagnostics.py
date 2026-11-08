"""Small, dependency-free helpers for persisted and displayed diagnostics."""
import re
from urllib.parse import urlsplit


def redact_diagnostic(value):
    text = str(value)

    def url(match):
        try:
            parsed = urlsplit(match.group())
            # Retain only origin: paths can contain credentials as well as queries.
            return f'{parsed.scheme}://{parsed.hostname or "[host]"}/[redacted]'
        except ValueError:
            return '[URL redacted]'

    text = re.sub(r'https?://[^\s<>"\']+', url, text)
    return re.sub(r'(?im)\b(cookie|authorization|sessdata|access_token|refresh_token|token)\s*[:=]\s*[^\r\n]+',
                  r'\1=[redacted]', text)


def failure_record(previous, stage, message, retryable=None, auto_retry_count=0):
    from datetime import datetime, timezone
    clean = redact_diagnostic(message)
    category = 'unknown'
    for marker, name in [('PoolTimeout', 'connection_pool'), ('连接池', 'connection_pool'),
                         ('ProxyError', 'proxy'), ('CERTIFICATE_VERIFY_FAILED', 'tls'),
                         ('Timeout', 'timeout'), ('HTTP', 'http'), ('状态码', 'http'),
                         ('文件读写', 'filesystem')]:
        if marker in clean:
            category = name
            break
    return {
        'stage': stage, 'category': category, 'message': clean[:16384],
        'time': datetime.now(timezone.utc).isoformat(), 'retryable': retryable,
        'auto_retry_count': auto_retry_count,
        'occurrences': previous.get('occurrences', 0) + 1,
    }
