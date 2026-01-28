"""
Script to analyze Douyin HTML and extract stream URLs
"""
import json
import requests
import re

# Load cookies
with open('data/douyin_cookies.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
cookies = data.get('cookies', {})
print(f'Loaded {len(cookies)} cookies')

# Fetch with cookies
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.douyin.com/'
}
resp = requests.get('https://live.douyin.com/999146174230', headers=headers, cookies=cookies)
html = resp.text
print(f'HTML size: {len(html)} bytes')

# Check for patterns
print(f'Has .flv: {".flv" in html}')
print(f'Has .m3u8: {".m3u8" in html}')
print(f'Has streamStore: {"streamStore" in html}')
print(f'Has pull_data: {"pull_data" in html}')
print(f'Has stream_url: {"stream_url" in html}')
print(f'Has H264: {"H264" in html}')
print(f'Has flv_pull: {"flv_pull" in html}')
print(f'Has hls_pull: {"hls_pull" in html}')

# Save HTML
with open('debug_stream_auth.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Saved to debug_stream_auth.html')

# Try to find stream URLs with regex
flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', html)
m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', html)
print(f'\nFound {len(flv_urls)} FLV URLs')
print(f'Found {len(m3u8_urls)} M3U8 URLs')

if flv_urls:
    print('\nFirst FLV URL:')
    print(flv_urls[0][:200])
