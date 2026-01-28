import requests
import uuid
import re

url = 'https://live.douyin.com/198671092027'

print("="*60)
print("Diagnóstico Detallado de Douyin")
print("="*60)

# Test 1: Request básico
print("\n[Test 1] Request básico")
cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.douyin.com/',
}

r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
print(f"Status: {r.status_code}")
print(f"HTML Length: {len(r.text)}")

# Test 2: Buscar patrones
print("\n[Test 2] Buscando patrones en HTML")
flv_urls = re.findall(r'"(https?://[^"]+\.flv[^"]*)"', r.text)
m3u8_urls = re.findall(r'"(https?://[^"]+\.m3u8[^"]*)"', r.text)
print(f"FLV URLs: {len(flv_urls)}")
print(f"M3U8 URLs: {len(m3u8_urls)}")

# Test 3: Buscar __pace_f
pace_matches = re.findall(r'__pace_f', r.text)
print(f"__pace_f encontrado: {len(pace_matches)} veces")

# Test 4: Buscar RENDER_DATA
render_matches = re.findall(r'RENDER_DATA|_ROUTER_DATA', r.text)
print(f"RENDER_DATA encontrado: {len(render_matches)} veces")

# Test 5: Mostrar primeros 500 caracteres del HTML
print("\n[Test 3] Primeros 500 caracteres del HTML:")
print(r.text[:500])

# Test 6: Buscar palabras clave
print("\n[Test 4] Palabras clave en HTML:")
keywords = ['stream', 'live', 'video', 'player', 'offline', 'error', 'redirect']
for keyword in keywords:
    count = r.text.lower().count(keyword)
    if count > 0:
        print(f"  {keyword}: {count} veces")

# Test 7: Verificar si es redirect
print("\n[Test 5] Headers de respuesta:")
print(f"  Content-Type: {r.headers.get('Content-Type')}")
print(f"  Content-Length: {r.headers.get('Content-Length')}")

# Test 8: Buscar scripts
print("\n[Test 6] Scripts en HTML:")
scripts = re.findall(r'<script[^>]*>', r.text)
print(f"  Scripts encontrados: {len(scripts)}")

print("\n" + "="*60)
print("Diagnóstico completado")
print("="*60)
