"""
Probar diferentes enfoques para obtener datos de Douyin
Basado en investigación de cómo otros scrapers lo hacen
"""

import requests
import uuid
import json
import re

url = 'https://live.douyin.com/198671092027'
room_id = '198671092027'

print("="*70)
print("ENFOQUE 1: Probar con diferentes User-Agents")
print("="*70)

# Probar con User-Agent de app móvil
mobile_headers = {
    'User-Agent': 'com.ss.android.ugc.aweme/110101 (Linux; U; Android 5.1.1; zh_CN; MI 9; Build/NMF26X; Cronet/TTNetVersion:b4d74d15 2020-04-23 QuicVersion:0144d358 2020-03-24)',
}

r1 = requests.get(url, headers=mobile_headers, timeout=10)
print(f"Mobile UA - Length: {len(r1.text)} bytes")

# Probar con User-Agent de desktop
desktop_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

r2 = requests.get(url, headers=desktop_headers, timeout=10)
print(f"Desktop UA - Length: {len(r2.text)} bytes")

print("\n" + "="*70)
print("ENFOQUE 2: Seguir redirects y analizar")
print("="*70)

session = requests.Session()
session.headers.update(desktop_headers)

# Permitir redirects
r3 = session.get(url, allow_redirects=True, timeout=10)
print(f"Final URL: {r3.url}")
print(f"Status: {r3.status_code}")
print(f"Length: {len(r3.text)} bytes")

# Ver si hay redirect a otra URL
if r3.url != url:
    print(f"✓ Redirected to: {r3.url}")

print("\n" + "="*70)
print("ENFOQUE 3: Buscar en response headers")
print("="*70)

for key, value in r3.headers.items():
    print(f"{key}: {value}")

print("\n" + "="*70)
print("ENFOQUE 4: Analizar contenido del HTML")
print("="*70)

html = r3.text

# Buscar cualquier JSON embebido
json_patterns = [
    r'<script[^>]*>\s*window\.__INIT_PROPS__\s*=\s*({.+?})\s*</script>',
    r'<script[^>]*>\s*self\.__pace_f\s*=\s*(\[.+?\])\s*</script>',
    r'<script[^>]*>.*?({.*?"roomStore".*?})',
]

for pattern in json_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f"\n✓ Pattern matched: {pattern[:60]}...")
        print(f"Matches: {len(matches)}")
        try:
            data = json.loads(matches[0])
            print("JSON parsed successfully!")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        except:
            print(f"Preview: {matches[0][:200]}")

# Buscar meta tags con datos
meta_content = re.findall(r'<meta[^>]+content="([^"]+)"[^>]*>', html)
print(f"\nMeta content tags: {len(meta_content)}")
for content in meta_content[:5]:
    if len(content) > 50:
        print(f"  {content[:100]}...")

print("\n" + "="*70)
print("ENFOQUE 5: Imprimir HTML completo para análisis manual")
print("="*70)
print(html)
