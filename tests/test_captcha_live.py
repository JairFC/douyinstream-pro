"""
Test del sistema de CAPTCHA con logs detallados
Ejecuta este script para probar la resolución de CAPTCHA
"""

import logging
import sys
from core.stream_engine import StreamEngine

# Configurar logging detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

print("="*80)
print("TEST: Sistema de Resolución de CAPTCHA de Douyin")
print("="*80)
print()
print("Este test intentará obtener el stream de Douyin.")
print("Si detecta CAPTCHA, se abrirá Chrome automáticamente.")
print()
print("INSTRUCCIONES:")
print("1. Cuando Chrome se abra, verás la página de Douyin con CAPTCHA")
print("2. Resuelve el CAPTCHA (desliza la pieza al lugar correcto)")
print("3. Espera a que la página se recargue")
print("4. Chrome se cerrará automáticamente")
print("5. El stream debería reproducirse")
print()
print("="*80)
print()

# URL de prueba
url = 'https://live.douyin.com/198671092027'

print(f"URL a probar: {url}")
print()
print("Iniciando StreamEngine...")
print()

try:
    # Crear StreamEngine
    se = StreamEngine()
    
    print("StreamEngine creado exitosamente")
    print()
    print("Intentando obtener stream URL...")
    print("(Si hay CAPTCHA, Chrome se abrirá en unos segundos)")
    print()
    
    # Intentar obtener stream
    stream_url = se.get_stream_url(url)
    
    print()
    print("="*80)
    print("RESULTADO")
    print("="*80)
    
    if stream_url:
        print("EXITO! Stream URL obtenida:")
        print()
        print(f"URL: {stream_url[:150]}...")
        print()
        print("El stream esta listo para reproducirse.")
    else:
        print("No se pudo obtener el stream URL")
        print()
        print("Posibles razones:")
        print("- El stream está offline")
        print("- No se resolvió el CAPTCHA correctamente")
        print("- Las cookies expiraron")
        
    print()
    print("="*80)
    
except KeyboardInterrupt:
    print()
    print("Test interrumpido por el usuario")
    
except Exception as e:
    print()
    print("="*80)
    print("ERROR")
    print("="*80)
    print(f"Error durante el test: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    print()
    print("Test finalizado")
