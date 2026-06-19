from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import json
import re

def validar_cupon_real(texto):
    if not texto:
        return None
    t = texto.strip().upper()
    # Filtro estricto para evitar textos descriptivos comunes
    palabras_ruido = [
        'CUPON', 'CODE', 'CODIGO', 'VER', 'INFO', 'COPIAR', 'OFERTA',
        'VER EN SITIO', 'IR A LA OFERTA', 'CHOLLOMETRO', 'VER CUPÓN',
        'GRATIS', 'DESCUENTO', 'PROMO', 'MÁS', 'MAS', 'MIRA'
    ]
    if t in palabras_ruido or len(t) < 3 or len(t) > 20:
        return None
    # Debe ser alfanumérico (letras y números mezclados o strings de cupones típicos)
    if re.match(r'^[A-Z0-9_\-]+$', t) and not t.isdigit():
        return t
    return None

def extraer_cupones_del_dom(urls_objetivo):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    print("Iniciando Chrome para extracción estructural de datos...")
    driver = webdriver.Chrome(options=chrome_options)
    
    cupones_capturados = []
    
    try:
        for url in urls_objetivo:
            print(f"\nNavegando en: {url}...")
            driver.get(url)
            time.sleep(5) # Espera de cortesía para renderizado básico
            
            # --- ESTRATEGIA 1: El objeto oculto de hidratación (__NEXT_DATA__ o similar) ---
            print(" Buscando datos estructurados ocultos en el HTML...")
            scripts = driver.find_elements(By.TAG_NAME, "script")
            found_in_hydration = False
            
            for script in scripts:
                try:
                    contenido = script.get_attribute("innerHTML")
                    if contenido and ('"vouchers"' in contenido or '"code"' in contenido) and '"props"' in contenido:
                        # Extraemos estructuras JSON masivas de inicialización de la página
                        datos_json = json.loads(contenido)
                        
                        # Buscador recursivo en el JSON extraído del script
                        def buscar_codigos(objeto):
                            if isinstance(objeto, dict):
                                if 'code' in objeto and objeto.get('code'):
                                    cup = validar_cupon_real(str(objeto['code']))
                                    if cup:
                                        tienda = objeto.get('merchant', {}).get('name', 'Tienda') if isinstance(objeto.get('merchant'), dict) else 'Chollometro'
                                        titulo = objeto.get('title', 'Cupón Promocional')
                                        cupones_capturados.append({
                                            'Cupón': cup,
                                            'Descripción': f"[{tienda}] {titulo}",
                                            'Fuente': url
                                        })
                                for k, v in objeto.items():
                                    buscar_codigos(v)
                            elif isinstance(objeto, list):
                                for item in objeto:
                                    buscar_codigos(item)
                                    
                        buscar_codigos(datos_json)
                        if len(cupones_capturados) > 0:
                            found_in_hydration = True
                            print(f" ¡Éxito! Se extrajeron {len(cupones_capturados)} cupones del bloque de datos nativo.")
                            break
                except Exception:
                    continue
            
            # --- ESTRATEGIA 2: Si falla la hidratación, raspamos las tarjetas directamente del DOM ---
            if not found_in_hydration:
                print(" Datos ocultos protegidos. Aplicando raspado directo por contenedores...")
                # Buscamos estructuras repetitivas que Chollometro usa para las ofertas/cupones
                tarjetas = driver.find_elements(By.XPATH, "//article | //div[contains(@class, 'thread') or contains(@class, 'voucher')]")
                
                for tarjeta in tarjetas:
                    try:
                        texto_tarjeta = tarjeta.text
                        lineas = [l.strip() for l in texto_tarjeta.split('\n') if l.strip()]
                        if not lineas: continue
                        
                        descripcion = lineas[0][:90] + "..."
                        
                        # Buscamos cualquier input, botón o elemento de texto que contenga patrones de código
                        codigo = None
                        elementos_codigo = tarjeta.find_elements(By.XPATH, ".//input | .//button | .//span[contains(@class, 'code')]")
                        
                        for el in elementos_codigo:
                            val = el.get_attribute("value") or el.text
                            codigo = validar_cupon_real(val)
                            if codigo: break
                        
                        # Si no se encuentra un código expuesto a simple vista, revisamos atributos data-*
                        if not codigo:
                            html_tarjeta = tarjeta.get_attribute("outerHTML")
                            matches = re.findall(r'data-code="([^"]+)"|data-coupon="([^"]+)"', html_tarjeta, re.IGNORECASE)
                            for m in matches:
                                val = m[0] or m[1]
                                codigo = validar_cupon_real(val)
                                if codigo: break
                        
                        if codigo:
                            cupones_capturados.append({
                                'Cupón': codigo,
                                'Descripción': descripcion,
                                'Fuente': url
                            })
                    except Exception:
                        continue
                        
    finally:
        driver.quit()
        
    return cupones_capturados

# --- EJECUCIÓN ---
urls = ["https://www.chollometro.com/cupones"]
resultados = extraer_cupones_del_dom(urls)

# Deduplicar
vistos = set()
cupones_unicos = []
for c in resultados:
    if c['Cupón'] not in vistos:
        vistos.add(c['Cupón'])
        cupones_unicos.append(c)

# Imprimir Tabla Final
print("\n" + "="*170)
print(f"{'CÓDIGO / CUPÓN':<30} | {'DESCRIPCIÓN':<80} | {'FUENTE'}")
print("-" * 170)
if not cupones_unicos:
    print(f"{'No se pudieron mapear cupones estructurales en esta sesión.':<135}")
else:
    for cupon in cupones_unicos:
        print(f"{cupon['Cupón']:<30} | {cupon['Descripción']:<80} | {cupon['Fuente']}")
print("="*170 + "\n")