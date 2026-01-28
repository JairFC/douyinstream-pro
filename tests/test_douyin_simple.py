import requests
import uuid
import re

# Fetch page
cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.douyin.com/',
}

print("Fetching Douyin page...")
r = requests.get('https://live.douyin.com/94782239787', headers=headers, cookies=cookies, timeout=10)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

# Method 1: Direct FLV URL extraction
print("\n=== Method 1: Direct FLV URL search ===")
flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', r.text)
print(f"FLV URLs found: {len(flv_urls)}")
if flv_urls:
    print(f"First FLV URL: {flv_urls[0][:120]}")
    print("\n*** SUCCESS - STREAM URL FOUND ***")

# Method 2: M3U8 URLs as fallback
print("\n=== Method 2: M3U8 URL search ===")
m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', r.text)
print(f"M3U8 URLs found: {len(m3u8_urls)}")
if m3u8_urls:
    print(f"First M3U8 URL: {m3u8_urls[0][:120]}")

# Method 3: Check for stream quality names
print("\n=== Method 3: Quality names search ===")
quality_matches = re.findall(r'"(origin|uhd|hd|sd|ld)"', r.text)
print(f"Quality names found: {set(quality_matches)}")

print("\n=== RESULT ===")
if flv_urls:
    print(f"BEST URL (FLV): {flv_urls[0]}")
elif m3u8_urls:
    print(f"BEST URL (M3U8): {m3u8_urls[0]}")
else:
    print("No stream URLs found")
