#!/usr/bin/env python3
"""Compare Range download settings; reads signed URL from stdin to keep it out of argv."""
import argparse
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from util.download_benchmark import benchmark  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample-mib', type=int, default=32, choices=range(1, 257))
    parser.add_argument('--rounds', type=int, default=2, choices=range(1, 4))
    parser.add_argument('--referer', default='https://www.bilibili.com/')
    parser.add_argument('--proxy', help='Explicit proxy URL; default is direct')
    args = parser.parse_args()
    url = sys.stdin.readline().strip()
    if not url.startswith(('http://', 'https://')):
        parser.error('stdin must contain an HTTP(S) media URL')
    results = []
    for round_number in range(args.rounds):
        cases = [(t, b) for t in (4, 6, 8) for b in (8192, 65536, 262144)]
        random.Random(round_number).shuffle(cases)
        for threads, buffer in cases:
            try:
                result = benchmark(url, threads=threads, buffer_size=buffer,
                                   sample_bytes=args.sample_mib * 1024 * 1024,
                                   headers={'Referer': args.referer, 'User-Agent': 'Mozilla/5.0'}, proxy=args.proxy)
            except Exception as error:
                result = {'threads': threads, 'buffer_size': buffer, 'error': type(error).__name__}
            result['round'] = round_number + 1
            results.append(result)
            print(json.dumps(result), flush=True)
    return int(any(r.get('error') or r.get('errors') for r in results))


if __name__ == '__main__':
    sys.exit(main())
