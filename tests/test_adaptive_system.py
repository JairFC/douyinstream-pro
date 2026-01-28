"""
Test script for adaptive extraction system
"""

from core.stream_engine import StreamEngine
from core.extraction_strategies import AdaptiveExtractor
import requests
import uuid

print("=" * 60)
print("Testing Adaptive Extraction System")
print("=" * 60)

# Test 1: StreamEngine integration
print("\n[Test 1] StreamEngine Integration")
print("-" * 60)
se = StreamEngine()
url = se.get_stream_url('https://live.douyin.com/94782239787')
print(f"Result: {'✓ SUCCESS' if url else '✗ FAILED'}")
if url:
    print(f"URL: {url[:100]}...")

# Test 2: Direct AdaptiveExtractor
print("\n[Test 2] Direct AdaptiveExtractor")
print("-" * 60)
cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r = requests.get('https://live.douyin.com/94782239787', headers=headers, cookies=cookies)

extractor = AdaptiveExtractor()
result = extractor.extract(r.text)

if result:
    print(f"✓ Extraction successful!")
    print(f"  Title: {result.get('title')}")
    print(f"  Author: {result.get('author')}")
    print(f"  Is Live: {result.get('is_live')}")
    print(f"  Qualities: {list(result.get('qualities', {}).keys())}")
    print(f"  URL: {result.get('url')[:100]}...")
else:
    print("✗ Extraction failed")

# Test 3: Strategy statistics
print("\n[Test 3] Strategy Statistics")
print("-" * 60)
stats = extractor.get_stats()
for strategy_name, strategy_stats in stats.items():
    print(f"{strategy_name}:")
    print(f"  Success: {strategy_stats['success']}")
    print(f"  Failure: {strategy_stats['failure']}")
    print(f"  Priority: {strategy_stats['priority']}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
