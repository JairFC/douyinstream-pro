"""
Comparación: URL que funcionaba vs URL nueva
"""

import requests
import uuid
import re

# URL que funcionaba antes
url_old = 'https://live.douyin.com/94782239787'
# URL nueva que el usuario dice está en vivo
url_new = 'https://live.douyin.com/198671092027'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.douyin.com/',
}

cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}

print("="*70)
print("COMPARACIÓN DE URLs")
print("="*70)

for name, url in [("URL Antigua", url_old), ("URL Nueva", url_new)]:
    print(f"\n[{name}] {url}")
    print("-"*70)
    
    r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"HTML Length: {len(r.text)} bytes")
    
    # Buscar URLs
    flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', r.text)
    m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', r.text)
    print(f"FLV URLs: {len(flv_urls)}")
    print(f"M3U8 URLs: {len(m3u8_urls)}")
    
    # Buscar patrones
    pace_f = len(re.findall(r'__pace_f', r.text))
    print(f"__pace_f: {pace_f}")
    
    # Buscar scripts
    scripts = len(re.findall(r'<script', r.text))
    print(f"Scripts: {scripts}")
    
    if flv_urls:
        print(f"\n✓ ENCONTRÓ STREAM!")
        print(f"Primera URL: {flv_urls[0][:100]}...")

print("\n" + "="*70)
print("CONCLUSIÓN")
print("="*70)
