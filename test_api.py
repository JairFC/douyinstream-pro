import requests
import uuid
import json
import re

# Probar diferentes métodos para obtener el stream
url = 'https://live.douyin.com/198671092027'

print("="*70)
print("MÉTODO 1: Probar API directa de Douyin")
print("="*70)

# Extraer room_id de la URL
room_id = url.split('/')[-1].split('?')[0]
print(f"Room ID: {room_id}")

# Probar API directa
api_url = f"https://live.douyin.com/webcast/room/web/enter/?aid=6383&app_name=douyin_web&live_id=1&device_platform=web&language=zh-CN&enter_from=web_live&cookie_enabled=true&screen_width=1920&screen_height=1080&browser_language=zh-CN&browser_platform=Win32&browser_name=Chrome&browser_version=131.0.0.0&web_rid={room_id}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': url,
}

cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}

try:
    r = requests.get(api_url, headers=headers, cookies=cookies, timeout=10)
    print(f"API Status: {r.status_code}")
    print(f"API Response length: {len(r.text)}")
    
    # Try to parse JSON
    try:
        data = r.json()
        print("JSON Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except:
        print("Not JSON, raw text:")
        print(r.text[:1000])
except Exception as e:
    print(f"API Error: {e}")

print("\n" + "="*70)
print("MÉTODO 2: Analizar HTML con diferentes patrones")
print("="*70)

r2 = requests.get(url, headers=headers, cookies=cookies, timeout=10)
html = r2.text

# Buscar RENDER_DATA o similar
patterns = [
    r'RENDER_DATA\s*=\s*({.+?})',
    r'_ROUTER_DATA\s*=\s*({.+?})',
    r'window\.__INIT_STATE__\s*=\s*({.+?})',
    r'window\.INITIAL_STATE\s*=\s*({.+?})',
    r'__INITIAL_STATE__\s*=\s*({.+?})',
]

for pattern in patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"\n✓ Found pattern: {pattern[:50]}")
        print(f"Matches: {len(matches)}")
        print(f"First match preview: {matches[0][:200]}")

print("\n" + "="*70)
print("MÉTODO 3: Buscar en scripts inline")
print("="*70)

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Scripts found: {len(scripts)}")

for i, script in enumerate(scripts):
    if 'stream' in script.lower() or 'flv' in script.lower() or 'm3u8' in script.lower():
        print(f"\n--- Script {i+1} contains stream data ---")
        print(script[:500])
