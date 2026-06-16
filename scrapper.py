import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

def buscar_cupones_en_sitio(driver, url_tienda):
    """
    Simula la búsqueda de cupones en una página específica.
    """
    cupones_encontrados = []
    
    try:
        driver.get(url_tienda)
        time.sleep(5) # Aumentamos un poco el tiempo para asegurar carga de JS
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Buscamos en contenedores, botones e inputs (donde suelen esconder el código)
        items = soup.find_all(['div', 'span', 'button', 'a', 'input'], class_=lambda x: x and ('coupon' in x.lower() or 'code' in x.lower() or 'offer' in x.lower()))
        
        # Si no hay nada, buscamos por texto (más agresivo)
        if not items:
            items = soup.find_all(['div', 'span', 'strong'], string=lambda s: s and ('cupón' in s.lower() or 'código' in s.lower()))

        if not items and "chollometro" in url_tienda:
            # Selector específico para los bloques de ofertas en Chollometro
            items = soup.select('strong.thread-title, span.cept-vote-temp')

        print(f"   -> DEBUG: Se encontraron {len(items)} posibles elementos de cupón en {url_tienda}")

        for item in items:
            texto_completo = item.get_text(separator=' ').strip().replace('\n', ' ')
            
            # 1. Buscar profundamente en atributos del elemento y TODOS sus hijos
            codigo_extraido = None
            palabras_ruido = ['CUPON', 'CODE', 'CODIGO', 'OFFER', 'SALE', 'VER', 'INFO', 'COPIAR', 'HTML', 'AEG', 'TEMU', 'HUAWEI', 'SHOP', 'TIKTOK', 'HOSTINGER', 'NUEVO', 'HOLA']
            
            # Revisamos el elemento y todos sus descendientes (botones, inputs, etc.)
            for el in [item] + item.find_all(True):
                for attr in ['data-code', 'data-clipboard-text', 'data-copy', 'data-coupon', 'value', 'title', 'data-text', 'placeholder']:
                    val = el.get(attr)
                    if val and isinstance(val, str) and 3 < len(val) < 25:
                        # Un cupón real suele tener letras Y números, o ser solo mayúsculas
                        if re.match(r'^[A-Z0-9_\-]+$', val) and val.upper() not in palabras_ruido:
                            codigo_extraido = val.strip()
                            break
                if codigo_extraido: break
            
            # 2. Si no hay atributo, usamos Regex para buscar patrones alfanuméricos (ej: SAVE20, PROMO2024)
            if not codigo_extraido:
                patrones = re.findall(r'\b[A-Z0-9]{5,15}\b', texto_completo)
                candidatos = [p for p in patrones if p not in palabras_ruido]
                codigo_extraido = candidatos[0] if candidatos else "Ver en sitio"

            if str(codigo_extraido).lower() in ["cupón", "código", "ver cupón", "oferta", "ver"]:
                codigo_extraido = "Ver en sitio"
            
            cupones_encontrados.append({
                'Cupón': str(codigo_extraido).upper() if codigo_extraido != "Ver en sitio" else codigo_extraido,
                'Descripción': texto_completo[:100] + "...",
                'Fuente': url_tienda,
                'Estado': 'Pendiente de Validar'
            })
            
    except Exception as e:
        print(f"Error raspando {url_tienda}: {e}")
        
    return cupones_encontrados

# Ejecución de ejemplo
urls = ["https://www.chollometro.com/cupones", "https://www.cuponation.es/"]
todos_los_cupones = []

# Configuración de Selenium: Iniciamos el navegador una sola vez
chrome_options = Options()
chrome_options.add_argument("--headless")
# Engañamos al sitio pareciendo un navegador real
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=chrome_options)

try:
    for url in urls:
        print(f"Buscando en: {url}...")
        resultados = buscar_cupones_en_sitio(driver, url)
        todos_los_cupones.extend(resultados)
finally:
    driver.quit() # Nos aseguramos de cerrar el navegador al terminar todo

# Deduplicación de resultados
vistos = set()
cupones_unicos = []
for c in todos_los_cupones:
    # Si el cupón es "Ver en sitio" y la descripción es similar, lo saltamos
    id_unico = (c['Cupón'], c['Descripción'][:40])
    if id_unico not in vistos:
        vistos.add(id_unico)
        cupones_unicos.append(c)

# Mostrar los cupones encontrados en la terminal
print("\n" + "="*170)
print(f"{'CÓDIGO / CUPÓN':<30} | {'DESCRIPCIÓN':<100} | {'FUENTE'}")
print("-" * 170)
for cupon in cupones_unicos:
    print(f"{str(cupon['Cupón']):<30} | {cupon['Descripción']:<100} | {cupon['Fuente']}")
print("="*170 + "\n")
