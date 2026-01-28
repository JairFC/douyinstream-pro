"""
Diagnóstico exhaustivo de Douyin
Prueba diferentes métodos para obtener el stream
"""

import requests
import uuid
import re
import json

url = 'https://live.douyin.com/198671092027'

print("="*70)
print("DIAGNÓSTICO EXHAUSTIVO - DOUYIN")
print("="*70)

# Test 1: Sin cookies
print("\n[Test 1] Request sin cookies")
print("-"*70)
headers_basic = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
r1 = requests.get(url, headers=headers_basic, timeout=10)
print(f"Status: {r1.status_code}")
print(f"Length: {len(r1.text)} bytes")
flv1 = len(re.findall(r'\.flv', r1.text))
print(f"FLV mentions: {flv1}")

# Test 2: Con cookie __ac_nonce
print("\n[Test 2] Request con cookie __ac_nonce")
print("-"*70)
cookies2 = {'__ac_nonce': uuid.uuid4().hex[:21]}
r2 = requests.get(url, headers=headers_basic, cookies=cookies2, timeout=10)
print(f"Status: {r2.status_code}")
print(f"Length: {len(r2.text)} bytes")
flv2 = len(re.findall(r'\.flv', r2.text))
print(f"FLV mentions: {flv2}")

# Test 3: Con headers completos
print("\n[Test 3] Request con headers completos")
print("-"*70)
headers_full = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.douyin.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}
cookies3 = {
    '__ac_nonce': uuid.uuid4().hex[:21],
    'ttwid': '1%7C' + uuid.uuid4().hex,
}
r3 = requests.get(url, headers=headers_full, cookies=cookies3, timeout=10)
print(f"Status: {r3.status_code}")
print(f"Length: {len(r3.text)} bytes")
flv3 = len(re.findall(r'\.flv', r3.text))
print(f"FLV mentions: {flv3}")

# Test 4: Intentar extraer con browser_cookie3
print("\n[Test 4] Intentando extraer cookies del navegador")
print("-"*70)
try:
    import browser_cookie3
    
    # Try Chrome
    try:
        cj = browser_cookie3.chrome(domain_name='.douyin.com')
        cookies_dict = {c.name: c.value for c in cj}
        print(f"Cookies de Chrome: {len(cookies_dict)}")
        if cookies_dict:
            print(f"Cookie names: {list(cookies_dict.keys())[:5]}")
            
            r4 = requests.get(url, headers=headers_full, cookies=cookies_dict, timeout=10)
            print(f"Status: {r4.status_code}")
            print(f"Length: {len(r4.text)} bytes")
            flv4 = len(re.findall(r'\.flv', r4.text))
            m3u8_4 = len(re.findall(r'\.m3u8', r4.text))
            print(f"FLV mentions: {flv4}")
            print(f"M3U8 mentions: {m3u8_4}")
            
            # Buscar URLs completas
            flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', r4.text)
            m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', r4.text)
            print(f"FLV URLs encontradas: {len(flv_urls)}")
            print(f"M3U8 URLs encontradas: {len(m3u8_urls)}")
            
            if flv_urls:
                print(f"\nPRIMERA URL FLV:")
                print(flv_urls[0][:150])
        else:
            print("No se encontraron cookies")
    except Exception as e:
        print(f"Error con Chrome: {e}")
        
except ImportError:
    print("browser_cookie3 no disponible")

# Test 5: Analizar contenido del HTML
print("\n[Test 5] Análisis del contenido HTML")
print("-"*70)
html = r3.text
print(f"Contiene 'offline': {'offline' in html.lower()}")
print(f"Contiene 'error': {'error' in html.lower()}")
print(f"Contiene 'redirect': {'redirect' in html.lower()}")
print(f"Contiene 'login': {'login' in html.lower()}")
print(f"Contiene 'script': {'<script' in html}")

# Buscar meta tags
meta_tags = re.findall(r'<meta[^>]+>', html)
print(f"Meta tags: {len(meta_tags)}")

# Buscar title
title_match = re.search(r'<title>([^<]+)</title>', html)
if title_match:
    print(f"Title: {title_match.group(1)}")

print("\n" + "="*70)
print("DIAGNÓSTICO COMPLETADO")
print("="*70)
