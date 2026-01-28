"""
Análisis profundo del HTML de Douyin
Vamos a extraer TODO el HTML y analizarlo en detalle
"""

import requests
import uuid
import re

url = 'https://live.douyin.com/198671092027'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.douyin.com/',
}

cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}

r = requests.get(url, headers=headers, cookies=cookies, timeout=10)

print("="*70)
print("ANÁLISIS COMPLETO DEL HTML")
print("="*70)
print(f"Status: {r.status_code}")
print(f"Length: {len(r.text)} bytes")
print("\n" + "="*70)
print("HTML COMPLETO:")
print("="*70)
print(r.text)
print("\n" + "="*70)
print("BÚSQUEDA DE PATRONES:")
print("="*70)

# Buscar todos los scripts
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
print(f"\nScripts encontrados: {len(scripts)}")
for i, script in enumerate(scripts):
    print(f"\n--- Script {i+1} ---")
    print(script[:500] if len(script) > 500 else script)

# Buscar meta tags
metas = re.findall(r'<meta[^>]+>', r.text)
print(f"\n\nMeta tags: {len(metas)}")
for meta in metas:
    print(meta)

# Buscar links
links = re.findall(r'<link[^>]+>', r.text)
print(f"\n\nLinks: {len(links)}")
for link in links:
    print(link)

# Buscar cualquier URL
all_urls = re.findall(r'https?://[^\s<>"]+', r.text)
print(f"\n\nTodas las URLs encontradas: {len(all_urls)}")
for url_found in all_urls[:20]:
    print(url_found)
