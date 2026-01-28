"""
Script de diagnóstico en tiempo real para depurar problemas de VLC y lag.
Ejecuta este script y sigue las instrucciones.
"""
import logging
import sys
import time

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

print("=" * 80)
print("DIAGNOSTICO EN TIEMPO REAL - DouyinStream Pro")
print("=" * 80)
print()

# Paso 1: Verificar cookies
print("[PASO 1] Verificando cookies...")
from core.captcha_solver import load_cookies
cookies = load_cookies()
print(f"  -> Cookies cargadas: {len(cookies)}")
print()

# Paso 2: Pedir URL al usuario
print("[PASO 2] Ingresa la URL del stream de Douyin:")
url = input("URL: ").strip()
if not url:
    url = "https://live.douyin.com/999146174230"  # URL por defecto
    print(f"  -> Usando URL por defecto: {url}")
print()

# Paso 3: Extraer stream
print("[PASO 3] Extrayendo información del stream...")
print("  (Esto puede tomar 5-10 segundos)")
print()

from core.douyin_extractor import DouyinExtractor
extractor = DouyinExtractor()

start_time = time.time()
result = extractor.extract_stream_url(url)
extraction_time = time.time() - start_time

print(f"  -> Tiempo de extracción: {extraction_time:.2f}s")
print()

if not result:
    print("[ERROR] No se pudo extraer el stream")
    print("Posibles causas:")
    print("  1. Stream está offline")
    print("  2. Cookies expiradas")
    print("  3. CAPTCHA bloqueando")
    sys.exit(1)

print("[EXITO] Stream extraído correctamente:")
print(f"  -> Título: {result.get('title')}")
print(f"  -> Autor: {result.get('author')}")
print(f"  -> En vivo: {result.get('is_live')}")
print(f"  -> Calidades: {list(result.get('qualities', {}).keys())}")
print()

stream_url = result.get('url')
if not stream_url:
    print("[ERROR] No se obtuvo URL del stream")
    sys.exit(1)

print(f"  -> URL del stream: {stream_url[:100]}...")
print()

# Paso 4: Verificar accesibilidad de la URL
print("[PASO 4] Verificando accesibilidad de la URL...")
import requests
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://live.douyin.com/'
}

try:
    response = requests.head(stream_url, headers=headers, timeout=10)
    print(f"  -> HTTP Status: {response.status_code}")
    if response.status_code == 200:
        print("  -> [OK] URL es accesible")
    else:
        print(f"  -> [ADVERTENCIA] Status code inesperado: {response.status_code}")
except Exception as e:
    print(f"  -> [ERROR] No se pudo acceder: {e}")
print()

# Paso 5: Información del sistema
print("[PASO 5] Información del sistema:")
try:
    import vlc
    print("  -> VLC Python: Instalado")
    print(f"  -> Versión VLC: {vlc.libvlc_get_version().decode()}")
except Exception as e:
    print(f"  -> VLC Python: ERROR - {e}")
print()

print("=" * 80)
print("DIAGNOSTICO COMPLETADO")
print("=" * 80)
print()
print("SIGUIENTE PASO:")
print("Si todo se ve bien arriba, el problema podría ser:")
print("  1. Múltiples procesos corriendo (revisar Task Manager)")
print("  2. VLC embebido con problemas de rendimiento")
print("  3. Buffering insuficiente")
print()
print("Presiona ENTER para continuar con prueba de VLC embebido...")
input()

# Paso 6: Probar VLC embebido
print()
print("[PASO 6] Probando VLC embebido...")
print("  (Se abrirá una ventana de prueba)")
print()

try:
    import customtkinter as ctk
    from ui.embedded_player import EmbeddedPlayer, is_vlc_available
    
    if not is_vlc_available():
        print("[ERROR] VLC no está disponible para embebido")
        sys.exit(1)
    
    print("  -> Creando ventana de prueba...")
    root = ctk.CTk()
    root.title("Prueba VLC Embebido")
    root.geometry("800x600")
    
    player = EmbeddedPlayer(root)
    player.pack(fill="both", expand=True)
    
    print("  -> Reproduciendo stream...")
    success = player.play(stream_url, "best")
    
    if success:
        print("  -> [OK] Reproducción iniciada")
        print()
        print("INSTRUCCIONES:")
        print("  - Observa si hay lag o stuttering")
        print("  - Cierra la ventana cuando termines de probar")
        print("  - Reporta cualquier error que veas")
        root.mainloop()
    else:
        print("  -> [ERROR] No se pudo iniciar reproducción")
        
except Exception as e:
    print(f"[ERROR] Error en prueba de VLC: {e}")
    import traceback
    traceback.print_exc()

print()
print("Diagnóstico finalizado.")
