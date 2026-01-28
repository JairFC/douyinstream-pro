"""
DouyinStream Pro - CAPTCHA Solver
Abre navegador para que usuario resuelva CAPTCHA manualmente.
"""

import logging
import time
from typing import Optional, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


class DouyinCaptchaSolver:
    """
    Resuelve CAPTCHA de Douyin abriendo navegador para interacción manual.
    """
    
    def __init__(self):
        self.driver = None
    
    def solve_captcha(self, url: str, timeout: int = 300) -> Dict[str, str]:
        """
        Abre navegador para que usuario resuelva CAPTCHA.
        
        Args:
            url: URL de Douyin que requiere CAPTCHA
            timeout: Tiempo máximo de espera en segundos (default: 5 minutos)
            
        Returns:
            Diccionario con cookies extraídas después de resolver CAPTCHA
            
        Raises:
            TimeoutError: Si el CAPTCHA no se resuelve en el tiempo límite
            Exception: Si hay error al abrir navegador o extraer cookies
        """
        try:
            logging.info("[CaptchaSolver] Iniciando resolución de CAPTCHA...")
            
            # Intentar Chrome primero, luego Edge
            driver_created = False
            
            # Intentar Chrome
            try:
                logging.info("[CaptchaSolver] Intentando abrir Chrome...")
                chrome_options = Options()
                chrome_options.add_argument('--start-maximized')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                driver_created = True
                logging.info("[CaptchaSolver] Chrome abierto exitosamente")
                
            except Exception as chrome_error:
                logging.warning(f"[CaptchaSolver] Chrome no disponible: {str(chrome_error)[:100]}")
                logging.info("[CaptchaSolver] Intentando abrir Edge...")
                
                try:
                    from selenium.webdriver.edge.service import Service as EdgeService
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    
                    edge_options = EdgeOptions()
                    edge_options.add_argument('--start-maximized')
                    edge_options.add_argument('--disable-blink-features=AutomationControlled')
                    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    
                    # Especificar ruta de Edge en Windows
                    import os
                    edge_paths = [
                        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                    ]
                    
                    edge_binary = None
                    for path in edge_paths:
                        if os.path.exists(path):
                            edge_binary = path
                            break
                    
                    if edge_binary:
                        edge_options.binary_location = edge_binary
                        logging.info(f"[CaptchaSolver] Edge encontrado en: {edge_binary}")
                    
                    edge_service = EdgeService(EdgeChromiumDriverManager().install())
                    self.driver = webdriver.Edge(service=edge_service, options=edge_options)
                    driver_created = True
                    logging.info("[CaptchaSolver] Edge abierto exitosamente")
                    
                except Exception as edge_error:
                    logging.error(f"[CaptchaSolver] Edge tampoco disponible: {str(edge_error)[:100]}")
                    raise Exception("No se pudo abrir Chrome ni Edge. Instala Chrome o verifica que Edge este instalado.")
            
            if not driver_created:
                raise Exception("No se pudo crear el navegador")
            
            logging.info(f"[CaptchaSolver] Navegador abierto, cargando: {url}")
            
            # Cargar URL
            self.driver.get(url)
            
            logging.info("[CaptchaSolver] Por favor resuelve el CAPTCHA en el navegador...")
            logging.info("[CaptchaSolver] El navegador se cerrará automáticamente cuando termines")
            
            # Esperar resolución
            self._wait_for_captcha_resolution(timeout)
            
            # Extraer cookies
            cookies = self._extract_cookies()
            
            logging.info(f"[CaptchaSolver] Cookies extraídas: {len(cookies)}")
            
            return cookies
            
        except Exception as e:
            logging.error(f"[CaptchaSolver] Error: {e}")
            raise
            
        finally:
            # Cerrar navegador
            if self.driver:
                try:
                    self.driver.quit()
                    logging.info("[CaptchaSolver] Navegador cerrado")
                except:
                    pass
    
    def _wait_for_captcha_resolution(self, timeout: int) -> None:
        """
        Espera hasta que el CAPTCHA sea resuelto.
        
        Detecta resolución cuando:
        - El HTML cambia de pequeño (CAPTCHA) a grande (contenido real)
        - Ya no contiene el script de TTGCaptcha
        """
        start_time = time.time()
        last_log_time = start_time
        
        while time.time() - start_time < timeout:
            try:
                # Obtener HTML actual
                html = self.driver.page_source
                html_size = len(html)
                
                # Log cada 10 segundos
                current_time = time.time()
                if current_time - last_log_time > 10:
                    elapsed = int(current_time - start_time)
                    logging.info(f"[CaptchaSolver] Esperando... ({elapsed}s, HTML: {html_size} bytes)")
                    last_log_time = current_time
                
                # Verificar si el CAPTCHA fue resuelto
                # Método 1: HTML grande (contenido cargado)
                if html_size > 50000:
                    logging.info("[CaptchaSolver] ✓ CAPTCHA resuelto! (HTML grande detectado)")
                    time.sleep(2)  # Esperar a que termine de cargar
                    return
                
                # Método 2: Ya no hay script de CAPTCHA
                if 'TTGCaptcha' not in html and html_size > 10000:
                    logging.info("[CaptchaSolver] ✓ CAPTCHA resuelto! (Script de CAPTCHA desapareció)")
                    time.sleep(2)
                    return
                
                # Método 3: Detectar elementos de contenido real
                if '<div id="root"' in html and 'middle_page_loading' not in html:
                    logging.info("[CaptchaSolver] ✓ CAPTCHA resuelto! (Contenido real detectado)")
                    time.sleep(2)
                    return
                
                time.sleep(1)
                
            except Exception as e:
                logging.debug(f"[CaptchaSolver] Error en verificación: {e}")
                time.sleep(1)
        
        raise TimeoutError(f"CAPTCHA no resuelto en {timeout} segundos")
    
    def _extract_cookies(self) -> Dict[str, str]:
        """
        Extrae cookies del navegador.
        
        Returns:
            Diccionario con nombre y valor de cada cookie
        """
        cookies = {}
        
        try:
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            # Log cookies importantes
            important_cookies = ['ttwid', '__ac_nonce', 'sessionid', 'sid_guard']
            found_important = [name for name in important_cookies if name in cookies]
            
            if found_important:
                logging.info(f"[CaptchaSolver] Cookies importantes encontradas: {found_important}")
            
        except Exception as e:
            logging.error(f"[CaptchaSolver] Error extrayendo cookies: {e}")
        
        return cookies


def test_captcha_solver():
    """Función de prueba para el solver."""
    solver = DouyinCaptchaSolver()
    
    try:
        cookies = solver.solve_captcha('https://live.douyin.com/198671092027')
        print(f"\n✓ Cookies obtenidas: {len(cookies)}")
        print(f"Cookie names: {list(cookies.keys())}")
        return cookies
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s'
    )
    
    print("="*70)
    print("TEST: CAPTCHA Solver")
    print("="*70)
    print("\nSe abrirá Chrome. Por favor resuelve el CAPTCHA.")
    print("El navegador se cerrará automáticamente cuando termines.\n")
    
    test_captcha_solver()
